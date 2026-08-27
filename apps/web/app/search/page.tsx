"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { search } from "@/lib/api-client";
import type { SearchResult } from "@/lib/types";

export default function SearchPage() {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Loading...</p>}>
      <SearchPageContent />
    </Suspense>
  );
}

function SearchPageContent() {
  const searchParams = useSearchParams();
  const sourceIdFilter = searchParams.get("source_id") ?? undefined;

  const [query, setQuery] = useState("");

  const searchMutation = useMutation({
    mutationFn: () => search({ query, sourceIds: sourceIdFilter ? [sourceIdFilter] : undefined }),
  });

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!query.trim()) return;
    searchMutation.mutate();
  };

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-2xl font-semibold">Search</h1>
      {sourceIdFilter && (
        <p className="text-sm text-slate-500">
          Scoped to one source.{" "}
          <Link href="/search" className="text-brand-600 hover:underline">
            Search everything instead
          </Link>
        </p>
      )}

      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask something your sources might answer..."
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={!query.trim() || searchMutation.isPending}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {searchMutation.isPending ? "Searching..." : "Search"}
        </button>
      </form>

      {searchMutation.isError && (
        <p className="text-sm text-red-600">{searchMutation.error.message}</p>
      )}

      {searchMutation.data?.not_found && (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-600">
          Nothing in your sources matched that query. Try rephrasing, or upload material that covers it.
        </div>
      )}

      <ul className="space-y-3">
        {searchMutation.data?.results.map((result) => (
          <SearchResultCard key={result.chunk_id} result={result} />
        ))}
      </ul>
    </div>
  );
}

function SearchResultCard({ result }: { result: SearchResult }) {
  const pageLabel =
    result.page_start === result.page_end
      ? `p. ${result.page_start}`
      : `pp. ${result.page_start}–${result.page_end}`;

  return (
    <li className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-2">
        <Link
          href={`/library/${result.source_id}`}
          className="font-medium text-brand-600 hover:underline"
        >
          {result.source_title}
        </Link>
        <span className="shrink-0 text-xs text-slate-500">{pageLabel}</span>
      </div>
      {result.heading_path.length > 0 && (
        <p className="mt-1 text-xs text-slate-500">{result.heading_path.join(" › ")}</p>
      )}
      <p className="mt-2 text-sm text-slate-700">{result.text}</p>
    </li>
  );
}
