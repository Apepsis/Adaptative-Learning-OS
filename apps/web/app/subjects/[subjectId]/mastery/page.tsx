"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getMisconceptionPatterns, getSubjectMastery, getWeaknesses, listConcepts } from "@/lib/api-client";
import type { ConceptMastery, Misconception } from "@/lib/types";

export default function MasteryPage() {
  const params = useParams<{ subjectId: string }>();
  const subjectId = params.subjectId;

  const { data: mastery, isPending } = useQuery({
    queryKey: ["subjects", subjectId, "mastery"],
    queryFn: () => getSubjectMastery(subjectId),
  });
  const { data: weaknesses } = useQuery({
    queryKey: ["subjects", subjectId, "mastery", "weaknesses"],
    queryFn: () => getWeaknesses(subjectId),
  });
  const { data: patterns } = useQuery({
    queryKey: ["subjects", subjectId, "mastery", "patterns"],
    queryFn: () => getMisconceptionPatterns(subjectId),
  });
  const { data: concepts } = useQuery({
    queryKey: ["subjects", subjectId, "concepts"],
    queryFn: () => listConcepts(subjectId),
  });

  const nameFor = (conceptId: string) =>
    concepts?.items.find((c) => c.id === conceptId)?.canonical_name ?? conceptId;

  return (
    <div className="max-w-3xl space-y-8">
      <Link href={`/subjects/${subjectId}`} className="text-sm text-brand-600 hover:underline">
        ← Back to subject
      </Link>
      <h1 className="text-2xl font-semibold">Mastery</h1>

      {weaknesses && weaknesses.items.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-slate-700">Weakest concepts</h2>
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {weaknesses.items.map((w) => (
              <li key={w.concept_id} className="p-4">
                <p className="font-medium">{w.concept_name}</p>
                <p className="mt-0.5 text-xs text-slate-500">{w.reason}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {patterns && patterns.items.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold text-slate-700">Recurring error patterns</h2>
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {patterns.items.map((p) => (
              <PatternRow key={p.id} pattern={p} conceptName={nameFor(p.concept_id)} />
            ))}
          </ul>
        </section>
      )}

      <section className="space-y-2">
        <h2 className="text-sm font-semibold text-slate-700">All concepts with practice evidence</h2>
        {isPending && <p className="text-sm text-slate-500">Loading...</p>}
        {mastery && mastery.items.length === 0 && (
          <p className="text-sm text-slate-500">
            No practice evidence yet — answer some questions to build a mastery picture per concept.
          </p>
        )}
        {mastery && mastery.items.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2">Concept</th>
                  <th className="px-4 py-2">Mastery</th>
                  <th className="px-4 py-2">Confidence</th>
                  <th className="px-4 py-2">Recent accuracy</th>
                  <th className="px-4 py-2">Attempts</th>
                </tr>
              </thead>
              <tbody>
                {mastery.items
                  .slice()
                  .sort((a, b) => a.p_mastery - b.p_mastery)
                  .map((row) => (
                    <MasteryRow key={row.concept_id} row={row} conceptName={nameFor(row.concept_id)} />
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function MasteryRow({ row, conceptName }: { row: ConceptMastery; conceptName: string }) {
  return (
    <tr className="border-b border-slate-100 last:border-0">
      <td className="px-4 py-2 font-medium">{conceptName}</td>
      <td className="px-4 py-2">
        <div className="flex items-center gap-2">
          <div className="h-2 w-24 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-brand-600"
              style={{ width: `${Math.round(row.p_mastery * 100)}%` }}
            />
          </div>
          <span className="text-xs text-slate-500">{Math.round(row.p_mastery * 100)}%</span>
        </div>
      </td>
      <td className="px-4 py-2 text-xs text-slate-500">{Math.round(row.mastery_confidence * 100)}%</td>
      <td className="px-4 py-2 text-xs text-slate-500">{Math.round(row.recent_accuracy * 100)}%</td>
      <td className="px-4 py-2 text-xs text-slate-500">{row.observation_count}</td>
    </tr>
  );
}

const STATUS_STYLES: Record<string, string> = {
  candidate: "bg-amber-100 text-amber-800",
  confirmed: "bg-red-100 text-red-800",
};

function PatternRow({ pattern, conceptName }: { pattern: Misconception; conceptName: string }) {
  return (
    <li className="flex items-center justify-between gap-3 p-4">
      <div>
        <p className="font-medium">{conceptName}</p>
        <p className="mt-0.5 text-xs text-slate-500">
          {pattern.error_type} · seen {pattern.event_count} time{pattern.event_count === 1 ? "" : "s"} across{" "}
          {pattern.distinct_question_count} question{pattern.distinct_question_count === 1 ? "" : "s"}
        </p>
      </div>
      <span
        className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${STATUS_STYLES[pattern.status] ?? ""}`}
      >
        {pattern.status}
      </span>
    </li>
  );
}
