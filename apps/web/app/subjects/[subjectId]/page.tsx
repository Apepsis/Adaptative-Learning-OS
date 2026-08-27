"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import {
  buildCurriculum,
  deleteConcept,
  getConcept,
  getSubject,
  listConcepts,
  mergeConcepts,
  updateConcept,
} from "@/lib/api-client";
import type { BuildCurriculumResponse, Concept, ConceptType } from "@/lib/types";

const TYPE_SECTIONS: { type: ConceptType; label: string }[] = [
  { type: "topic", label: "Topics" },
  { type: "subtopic", label: "Subtopics" },
  { type: "concept", label: "Concepts" },
  { type: "skill", label: "Skills" },
];

export default function SubjectDetailPage() {
  const params = useParams<{ subjectId: string }>();
  const subjectId = params.subjectId;
  const queryClient = useQueryClient();

  const { data: subject } = useQuery({
    queryKey: ["subjects", subjectId],
    queryFn: () => getSubject(subjectId),
  });

  const { data: concepts, isPending } = useQuery({
    queryKey: ["subjects", subjectId, "concepts"],
    queryFn: () => listConcepts(subjectId),
  });

  const [buildResult, setBuildResult] = useState<BuildCurriculumResponse | null>(null);
  const buildMutation = useMutation({
    mutationFn: () => buildCurriculum(subjectId),
    onSuccess: (result) => {
      setBuildResult(result);
      queryClient.invalidateQueries({ queryKey: ["subjects", subjectId, "concepts"] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{subject?.name ?? "Subject"}</h1>
        <button
          onClick={() => buildMutation.mutate()}
          disabled={buildMutation.isPending}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {buildMutation.isPending ? "Building..." : "Build curriculum"}
        </button>
      </div>

      <nav className="flex gap-4 border-b border-slate-200 pb-2 text-sm">
        <Link href={`/subjects/${subjectId}/definitions`} className="text-brand-600 hover:underline">
          Definitions
        </Link>
        <Link href={`/subjects/${subjectId}/flashcards`} className="text-brand-600 hover:underline">
          Flashcards
        </Link>
        <Link href={`/subjects/${subjectId}/study-guide`} className="text-brand-600 hover:underline">
          Study guide
        </Link>
        <Link href={`/subjects/${subjectId}/questions`} className="text-brand-600 hover:underline">
          Questions
        </Link>
      </nav>

      {buildMutation.isError && (
        <p className="text-sm text-red-600">{buildMutation.error.message}</p>
      )}
      {buildResult && (
        <div className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">
          {buildResult.concepts_created} concept{buildResult.concepts_created === 1 ? "" : "s"} created,{" "}
          {buildResult.concepts_updated} updated, {buildResult.edges_created} relationship
          {buildResult.edges_created === 1 ? "" : "s"} added, from {buildResult.chunks_considered} chunks of
          your sources.
        </div>
      )}

      {isPending && <p className="text-sm text-slate-500">Loading...</p>}

      {concepts && concepts.items.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-600">
          No concepts yet. Upload sources to this subject, wait for them to finish processing, then
          click &quot;Build curriculum&quot; above.
        </div>
      )}

      {TYPE_SECTIONS.map(({ type, label }) => {
        const items = concepts?.items.filter((c) => c.concept_type === type) ?? [];
        if (items.length === 0) return null;
        return (
          <section key={type} className="space-y-2">
            <h2 className="text-sm font-semibold text-slate-700">{label}</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {items.map((concept) => (
                <ConceptCard
                  key={concept.id}
                  subjectId={subjectId}
                  concept={concept}
                  allConcepts={concepts?.items ?? []}
                />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

const STATUS_STYLES: Record<string, string> = {
  PROPOSED: "bg-amber-100 text-amber-800",
  APPROVED: "bg-emerald-100 text-emerald-800",
  REJECTED: "bg-slate-200 text-slate-600",
  MERGED: "bg-slate-200 text-slate-600",
};

function ConceptCard({
  subjectId,
  concept,
  allConcepts,
}: {
  subjectId: string;
  concept: Concept;
  allConcepts: Concept[];
}) {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [mergeTargetId, setMergeTargetId] = useState("");

  const { data: detail } = useQuery({
    queryKey: ["subjects", subjectId, "concepts", concept.id],
    queryFn: () => getConcept(subjectId, concept.id),
    enabled: expanded,
  });

  const invalidateConcepts = () =>
    queryClient.invalidateQueries({ queryKey: ["subjects", subjectId, "concepts"] });

  const statusMutation = useMutation({
    mutationFn: (status: string) => updateConcept(subjectId, concept.id, { status }),
    onSuccess: invalidateConcepts,
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteConcept(subjectId, concept.id),
    onSuccess: invalidateConcepts,
  });

  const mergeMutation = useMutation({
    mutationFn: () => mergeConcepts(subjectId, mergeTargetId, concept.id),
    onSuccess: invalidateConcepts,
  });

  const otherConcepts = allConcepts.filter((c) => c.id !== concept.id);

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="font-medium">{concept.canonical_name}</p>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${STATUS_STYLES[concept.status]}`}>
          {concept.status}
        </span>
      </div>
      {concept.definition && <p className="mt-1 text-sm text-slate-600">{concept.definition}</p>}

      <button onClick={() => setExpanded((v) => !v)} className="mt-2 text-xs text-brand-600 hover:underline">
        {expanded ? "Hide relationships" : "Show relationships"}
      </button>

      {expanded && detail && (
        <div className="mt-2 space-y-1 border-t border-slate-100 pt-2 text-xs text-slate-600">
          {detail.outgoing_edges.length === 0 && detail.incoming_edges.length === 0 && (
            <p className="text-slate-400">No relationships yet.</p>
          )}
          {detail.outgoing_edges.map((edge) => (
            <p key={edge.id}>
              {edge.relation} →{" "}
              {allConcepts.find((c) => c.id === edge.target_concept_id)?.canonical_name ?? "?"}
            </p>
          ))}
          {detail.incoming_edges.map((edge) => (
            <p key={edge.id}>
              {allConcepts.find((c) => c.id === edge.source_concept_id)?.canonical_name ?? "?"} →{" "}
              {edge.relation} → this
            </p>
          ))}
          <p className="text-slate-400">{detail.evidence.length} source excerpt(s) cited.</p>
        </div>
      )}

      <Link
        href={`/subjects/${subjectId}/concepts/${concept.id}`}
        className="mt-2 block text-xs text-brand-600 hover:underline"
      >
        View lesson →
      </Link>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {concept.status === "PROPOSED" && (
          <>
            <button
              onClick={() => statusMutation.mutate("APPROVED")}
              className="rounded bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-100"
            >
              Approve
            </button>
            <button
              onClick={() => statusMutation.mutate("REJECTED")}
              className="rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-200"
            >
              Reject
            </button>
          </>
        )}
        <button
          onClick={() => deleteMutation.mutate()}
          className="rounded bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100"
        >
          Delete
        </button>
      </div>

      {otherConcepts.length > 0 && (
        <div className="mt-2 flex gap-2">
          <select
            value={mergeTargetId}
            onChange={(e) => setMergeTargetId(e.target.value)}
            className="min-w-0 flex-1 rounded-md border border-slate-300 px-2 py-1 text-xs"
          >
            <option value="">Merge into...</option>
            {otherConcepts.map((c) => (
              <option key={c.id} value={c.id}>
                {c.canonical_name}
              </option>
            ))}
          </select>
          <button
            onClick={() => mergeTargetId && mergeMutation.mutate()}
            disabled={!mergeTargetId || mergeMutation.isPending}
            className="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium hover:bg-slate-200 disabled:opacity-50"
          >
            Merge
          </button>
        </div>
      )}
    </div>
  );
}
