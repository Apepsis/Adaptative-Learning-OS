"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { createSubject, listSubjects } from "@/lib/api-client";

const subjectSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  subject_type: z.string().optional(),
});

type SubjectFormValues = z.infer<typeof subjectSchema>;

export default function SubjectsPage() {
  const queryClient = useQueryClient();
  const { data, isPending } = useQuery({ queryKey: ["subjects"], queryFn: listSubjects });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<SubjectFormValues>({ resolver: zodResolver(subjectSchema) });

  const createMutation = useMutation({
    mutationFn: createSubject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subjects"] });
      reset();
    },
  });

  const onSubmit = handleSubmit((values) => createMutation.mutate(values));

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold">Subjects</h1>

      <form onSubmit={onSubmit} className="flex flex-wrap items-start gap-3 rounded-lg border border-slate-200 bg-white p-4">
        <div>
          <input
            {...register("name")}
            placeholder="e.g. IB Physics HL"
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>}
        </div>
        <input
          {...register("subject_type")}
          placeholder="Type (optional, e.g. physics)"
          className="rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={isSubmitting || createMutation.isPending}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          Create subject
        </button>
        {createMutation.isError && (
          <p className="w-full text-sm text-red-600">{createMutation.error.message}</p>
        )}
      </form>

      {isPending && <p className="text-sm text-slate-500">Loading subjects...</p>}

      {data && data.items.length === 0 && (
        <p className="text-sm text-slate-500">No subjects yet. Create one above.</p>
      )}

      <ul className="grid gap-3 sm:grid-cols-2">
        {data?.items.map((subject) => (
          <li key={subject.id}>
            <Link
              href={`/subjects/${subject.id}`}
              className="block rounded-lg border border-slate-200 bg-white p-4 transition hover:border-brand-500 hover:shadow"
            >
              <p className="font-medium">{subject.name}</p>
              {subject.subject_type && (
                <p className="mt-1 text-xs uppercase tracking-wide text-slate-500">
                  {subject.subject_type}
                </p>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
