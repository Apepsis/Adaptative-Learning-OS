"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { deleteSource, getSource, reprocessSource } from "@/lib/api-client";
import { StatusBadge } from "@/components/StatusBadge";
import type { SourceStatus } from "@/lib/types";

const ACTIVE_STATUSES: SourceStatus[] = ["UPLOADED", "PARSING"];

export default function SourceDetailPage() {
  const params = useParams<{ sourceId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: source, isPending } = useQuery({
    queryKey: ["sources", params.sourceId],
    queryFn: () => getSource(params.sourceId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && ACTIVE_STATUSES.includes(status) ? 2_000 : false;
    },
  });

  const reprocessMutation = useMutation({
    mutationFn: () => reprocessSource(params.sourceId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sources", params.sourceId] }),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteSource(params.sourceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      router.push("/library");
    },
  });

  if (isPending) return <p className="text-sm text-slate-500">Loading...</p>;
  if (!source) return <p className="text-sm text-red-600">Source not found.</p>;

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{source.title}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {source.type.toUpperCase()} &middot; {source.mime_type}
          </p>
        </div>
        <StatusBadge status={source.status} />
      </div>

      {(source.status === "FAILED" || source.status === "UNSUPPORTED") && source.error_message && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{source.error_message}</div>
      )}

      {source.status === "READY" && (
        <Link
          href={`/search?source_id=${source.id}`}
          className="inline-block rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          Search this source
        </Link>
      )}

      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 rounded-lg border border-slate-200 bg-white p-4 text-sm">
        <dt className="text-slate-500">Original filename</dt>
        <dd>{source.original_filename ?? "—"}</dd>
        <dt className="text-slate-500">Size</dt>
        <dd>{(source.size_bytes / 1024).toFixed(0)} KB</dd>
        <dt className="text-slate-500">Uploaded</dt>
        <dd>{new Date(source.created_at).toLocaleString()}</dd>
        <dt className="text-slate-500">Last updated</dt>
        <dd>{new Date(source.updated_at).toLocaleString()}</dd>
      </dl>

      <div className="flex gap-3">
        <button
          onClick={() => reprocessMutation.mutate()}
          disabled={reprocessMutation.isPending}
          className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
        >
          Reprocess
        </button>
        <button
          onClick={() => {
            if (confirm("Delete this source? This cannot be undone.")) {
              deleteMutation.mutate();
            }
          }}
          disabled={deleteMutation.isPending}
          className="rounded-md border border-red-200 bg-white px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
        >
          Delete
        </button>
      </div>
    </div>
  );
}
