"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { createNotebook, listNotebooks } from "@/lib/api-client";

export default function NotebooksPage() {
  const queryClient = useQueryClient();
  const { data, isPending } = useQuery({ queryKey: ["notebooks"], queryFn: listNotebooks });

  const [title, setTitle] = useState("");

  const createMutation = useMutation({
    mutationFn: () => createNotebook({ title }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notebooks"] });
      setTitle("");
    },
  });

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!title.trim()) return;
    createMutation.mutate();
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Notebooks</h1>
      <p className="text-sm text-slate-600">
        A notebook is a focused set of sources you chat with — grounded answers, always cited.
      </p>

      <form onSubmit={onSubmit} className="flex gap-2 rounded-lg border border-slate-200 bg-white p-4">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. IB Physics HL — Mechanics"
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={!title.trim() || createMutation.isPending}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          New notebook
        </button>
      </form>

      {isPending && <p className="text-sm text-slate-500">Loading...</p>}

      {data && data.items.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-600">
          No notebooks yet. Create one above.
        </div>
      )}

      <ul className="grid gap-3 sm:grid-cols-2">
        {data?.items.map((notebook) => (
          <li key={notebook.id}>
            <Link
              href={`/notebooks/${notebook.id}`}
              className="block rounded-lg border border-slate-200 bg-white p-4 transition hover:border-brand-500 hover:shadow"
            >
              <p className="font-medium">{notebook.title}</p>
              {notebook.description && (
                <p className="mt-1 text-sm text-slate-500">{notebook.description}</p>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
