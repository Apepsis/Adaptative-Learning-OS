"use client";

import { useQuery } from "@tanstack/react-query";
import { getHealthReady } from "@/lib/api-client";

export function ApiStatus() {
  const { data, isPending, isError } = useQuery({
    queryKey: ["health", "ready"],
    queryFn: getHealthReady,
    refetchInterval: 15_000,
  });

  if (isPending) {
    return <StatusPill label="Checking API..." tone="pending" />;
  }

  if (isError || data?.status !== "ok") {
    return <StatusPill label="API unreachable" tone="error" />;
  }

  return <StatusPill label="API ready" tone="ok" />;
}

function StatusPill({ label, tone }: { label: string; tone: "ok" | "pending" | "error" }) {
  const toneClasses = {
    ok: "bg-emerald-100 text-emerald-800",
    pending: "bg-slate-200 text-slate-600",
    error: "bg-red-100 text-red-800",
  }[tone];

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ${toneClasses}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label}
    </span>
  );
}
