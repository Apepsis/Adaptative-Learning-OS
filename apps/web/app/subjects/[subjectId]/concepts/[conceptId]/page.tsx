"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getConcept, listConcepts } from "@/lib/api-client";

export default function LessonPage() {
  const params = useParams<{ subjectId: string; conceptId: string }>();
  const { subjectId, conceptId } = params;

  const { data: concept, isPending } = useQuery({
    queryKey: ["subjects", subjectId, "concepts", conceptId],
    queryFn: () => getConcept(subjectId, conceptId),
  });

  const { data: allConcepts } = useQuery({
    queryKey: ["subjects", subjectId, "concepts"],
    queryFn: () => listConcepts(subjectId),
  });

  if (isPending) return <p className="text-sm text-slate-500">Loading...</p>;
  if (!concept) return <p className="text-sm text-red-600">Concept not found.</p>;

  const nameOf = (id: string) => allConcepts?.items.find((c) => c.id === id)?.canonical_name ?? "?";
  const prerequisites = concept.incoming_edges.filter((e) => e.relation === "PREREQUISITE_OF");
  const partOf = concept.outgoing_edges.filter((e) => e.relation === "PART_OF");
  const otherOutgoing = concept.outgoing_edges.filter((e) => e.relation !== "PART_OF");
  const otherIncoming = concept.incoming_edges.filter((e) => e.relation !== "PREREQUISITE_OF");

  return (
    <div className="max-w-2xl space-y-6">
      <Link href={`/subjects/${subjectId}`} className="text-sm text-brand-600 hover:underline">
        ← Back to subject
      </Link>

      <div>
        <span className="text-xs uppercase tracking-wide text-slate-500">{concept.concept_type}</span>
        <h1 className="text-2xl font-semibold">{concept.canonical_name}</h1>
      </div>

      {concept.definition && (
        <p className="rounded-lg border border-slate-200 bg-white p-4 text-slate-700">
          {concept.definition}
        </p>
      )}

      {partOf.length > 0 && (
        <p className="text-sm text-slate-600">
          Part of:{" "}
          {partOf.map((e, i) => (
            <span key={e.id}>
              {i > 0 && ", "}
              <Link
                href={`/subjects/${subjectId}/concepts/${e.target_concept_id}`}
                className="text-brand-600 hover:underline"
              >
                {nameOf(e.target_concept_id)}
              </Link>
            </span>
          ))}
        </p>
      )}

      {prerequisites.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-700">Prerequisites</h2>
          <ul className="mt-1 list-inside list-disc text-sm text-slate-600">
            {prerequisites.map((e) => (
              <li key={e.id}>
                <Link
                  href={`/subjects/${subjectId}/concepts/${e.source_concept_id}`}
                  className="text-brand-600 hover:underline"
                >
                  {nameOf(e.source_concept_id)}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {(otherOutgoing.length > 0 || otherIncoming.length > 0) && (
        <div>
          <h2 className="text-sm font-semibold text-slate-700">Other relationships</h2>
          <ul className="mt-1 list-inside list-disc text-sm text-slate-600">
            {otherOutgoing.map((e) => (
              <li key={e.id}>
                {e.relation} → {nameOf(e.target_concept_id)}
              </li>
            ))}
            {otherIncoming.map((e) => (
              <li key={e.id}>
                {nameOf(e.source_concept_id)} → {e.relation} → this
              </li>
            ))}
          </ul>
        </div>
      )}

      {concept.evidence.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-700">From your sources</h2>
          <ul className="mt-2 space-y-2">
            {concept.evidence.map((excerpt) => (
              <li key={excerpt.chunk_id} className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
                <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
                  <Link href={`/library/${excerpt.source_id}`} className="text-brand-600 hover:underline">
                    {excerpt.source_title}
                  </Link>
                  <span>
                    {excerpt.page_start === excerpt.page_end
                      ? `p. ${excerpt.page_start}`
                      : `pp. ${excerpt.page_start}–${excerpt.page_end}`}
                  </span>
                </div>
                <p className="text-slate-700">{excerpt.text}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
