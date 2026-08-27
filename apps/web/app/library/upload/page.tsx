"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { listSubjects, uploadSource } from "@/lib/api-client";

const ACCEPTED_EXTENSIONS = ".pdf,.docx,.pptx,.png,.jpg,.jpeg,.webp";

export default function UploadPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: subjectsData } = useQuery({ queryKey: ["subjects"], queryFn: listSubjects });

  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [subjectId, setSubjectId] = useState("");

  const uploadMutation = useMutation({
    mutationFn: uploadSource,
    onSuccess: (source) => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      router.push(`/library/${source.id}`);
    },
  });

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) return;
    uploadMutation.mutate({
      file,
      title: title || undefined,
      subjectId: subjectId || undefined,
    });
  };

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="text-2xl font-semibold">Upload a source</h1>
      <p className="text-sm text-slate-600">
        PDF, DOCX, PPTX, PNG, or JPEG. The file type is verified from its
        contents, not just its extension.
      </p>

      <form onSubmit={onSubmit} className="space-y-4 rounded-lg border border-slate-200 bg-white p-5">
        <div>
          <label className="block text-sm font-medium text-slate-700">File</label>
          <input
            type="file"
            accept={ACCEPTED_EXTENSIONS}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="mt-1 block w-full text-sm"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700">Title (optional)</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={file?.name ?? "Defaults to the filename"}
            className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700">Subject (optional)</label>
          <select
            value={subjectId}
            onChange={(e) => setSubjectId(e.target.value)}
            className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">No subject</option>
            {subjectsData?.items.map((subject) => (
              <option key={subject.id} value={subject.id}>
                {subject.name}
              </option>
            ))}
          </select>
        </div>

        <button
          type="submit"
          disabled={!file || uploadMutation.isPending}
          className="w-full rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {uploadMutation.isPending ? "Uploading..." : "Upload"}
        </button>

        {uploadMutation.isError && (
          <p className="text-sm text-red-600">{uploadMutation.error.message}</p>
        )}
      </form>
    </div>
  );
}
