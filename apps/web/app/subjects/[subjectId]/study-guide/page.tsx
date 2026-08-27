"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { ApiError, generateStudyGuide, getStudyGuide } from "@/lib/api-client";

export default function StudyGuidePage() {
  const params = useParams<{ subjectId: string }>();
  const subjectId = params.subjectId;
  const queryClient = useQueryClient();

  const { data, isPending, error } = useQuery({
    queryKey: ["subjects", subjectId, "study-guide"],
    queryFn: () => getStudyGuide(subjectId),
    retry: false,
  });

  const generateMutation = useMutation({
    mutationFn: () => generateStudyGuide(subjectId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["subjects", subjectId, "study-guide"] }),
  });

  const notFoundYet = error instanceof ApiError && error.status === 404;

  return (
    <div className="max-w-2xl space-y-6">
      <Link href={`/subjects/${subjectId}`} className="text-sm text-brand-600 hover:underline">
        ← Back to subject
      </Link>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Study guide</h1>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {generateMutation.isPending ? "Generating..." : data ? "Regenerate" : "Generate"}
        </button>
      </div>

      {generateMutation.isError && (
        <p className="text-sm text-red-600">{generateMutation.error.message}</p>
      )}

      {isPending && <p className="text-sm text-slate-500">Loading...</p>}

      {notFoundYet && !generateMutation.isPending && (
        <p className="text-sm text-slate-500">
          No study guide yet. Build the curriculum for this subject, then click &quot;Generate&quot;
          above.
        </p>
      )}

      {data && (
        <article
          className="rounded-lg border border-slate-200 bg-white p-6 text-sm leading-relaxed text-slate-800
          [&_h2]:mt-5 [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:first:mt-0
          [&_h3]:mt-4 [&_h3]:text-base [&_h3]:font-semibold
          [&_p]:mt-2 [&_ul]:mt-2 [&_ul]:list-inside [&_ul]:list-disc [&_li]:mt-1"
        >
          <ReactMarkdown>{data.content}</ReactMarkdown>
        </article>
      )}
    </div>
  );
}
