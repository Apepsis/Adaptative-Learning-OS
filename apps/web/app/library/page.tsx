"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { listSources } from "@/lib/api-client";
import { formatBytes } from "@/lib/format";
import { StatusBadge } from "@/components/StatusBadge";

export default function LibraryPage() {
  const { data, isPending, isError } = useQuery({
    queryKey: ["sources"],
    queryFn: () => listSources(),
    refetchInterval: 5_000,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Library</h1>
        <Link
          href="/library/upload"
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          Upload source
        </Link>
      </div>

      {isPending && <p className="text-sm text-slate-500">Loading sources...</p>}
      {isError && <p className="text-sm text-red-600">Could not load sources.</p>}

      {data && data.items.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center">
          <p className="text-slate-600">No sources yet.</p>
          <Link href="/library/upload" className="mt-2 inline-block text-sm text-brand-600 hover:underline">
            Upload your first PDF, slide deck, or photo
          </Link>
        </div>
      )}

      <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
        {data?.items.map((source) => (
          <li key={source.id}>
            <Link
              href={`/library/${source.id}`}
              className="flex items-center justify-between gap-4 px-4 py-3 hover:bg-slate-50"
            >
              <div className="min-w-0">
                <p className="truncate font-medium">{source.title}</p>
                <p className="text-xs text-slate-500">
                  {source.type.toUpperCase()} &middot; {formatBytes(source.size_bytes)}
                </p>
              </div>
              <StatusBadge status={source.status} />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
