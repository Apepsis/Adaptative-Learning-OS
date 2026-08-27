import type { SourceStatus } from "@/lib/types";

const STYLES: Record<SourceStatus, string> = {
  UPLOADED: "bg-amber-100 text-amber-800",
  QUEUED: "bg-brand-100 text-brand-700",
  FAILED: "bg-red-100 text-red-800",
};

export function StatusBadge({ status }: { status: SourceStatus }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLES[status]}`}>
      {status}
    </span>
  );
}
