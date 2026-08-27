import Link from "next/link";
import { ApiStatus } from "@/components/ApiStatus";

export default function HomePage() {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Welcome back</h1>
        <ApiStatus />
      </div>

      <p className="max-w-2xl text-slate-600">
        This is Phase 0 + Phase 1 of the Adaptive Learning OS: the repository
        foundation and the source library. Upload material and track its
        status here. Curriculum, practice, mastery tracking, and the
        adaptive planner ship in later phases — see{" "}
        <code className="rounded bg-slate-200 px-1.5 py-0.5 text-sm">
          docs/architecture/roadmap.md
        </code>
        .
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        <Link
          href="/library"
          className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-brand-500 hover:shadow"
        >
          <h2 className="font-medium">Library</h2>
          <p className="mt-1 text-sm text-slate-600">
            Upload PDFs, slides, and photos. Track ingestion status.
          </p>
        </Link>
        <Link
          href="/subjects"
          className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-brand-500 hover:shadow"
        >
          <h2 className="font-medium">Subjects</h2>
          <p className="mt-1 text-sm text-slate-600">
            Create subjects to organize your sources.
          </p>
        </Link>
      </div>
    </div>
  );
}
