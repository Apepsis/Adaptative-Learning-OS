"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { listConcepts } from "@/lib/api-client";

export default function DefinitionsPage() {
  const params = useParams<{ subjectId: string }>();
  const subjectId = params.subjectId;

  const { data, isPending } = useQuery({
    queryKey: ["subjects", subjectId, "concepts"],
    queryFn: () => listConcepts(subjectId),
  });

  const [query, setQuery] = useState("");

  const defined = (data?.items ?? [])
    .filter((c) => c.definition && c.status !== "REJECTED")
    .filter((c) => c.canonical_name.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => a.canonical_name.localeCompare(b.canonical_name));

  return (
    <div className="max-w-2xl space-y-6">
      <Link href={`/subjects/${subjectId}`} className="text-sm text-brand-600 hover:underline">
        ← Back to subject
      </Link>
      <h1 className="text-2xl font-semibold">Definitions</h1>

      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Filter..."
        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
      />

      {isPending && <p className="text-sm text-slate-500">Loading...</p>}
      {data && defined.length === 0 && (
        <p className="text-sm text-slate-500">
          No definitions yet — build the curriculum for this subject first.
        </p>
      )}

      <dl className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
        {defined.map((concept) => (
          <div key={concept.id} className="p-4">
            <dt>
              <Link
                href={`/subjects/${subjectId}/concepts/${concept.id}`}
                className="font-medium text-brand-600 hover:underline"
              >
                {concept.canonical_name}
              </Link>
            </dt>
            <dd className="mt-1 text-sm text-slate-600">{concept.definition}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
