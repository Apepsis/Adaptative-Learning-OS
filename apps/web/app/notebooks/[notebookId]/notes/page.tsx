"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { createNote, deleteNote, listNotes, updateNote } from "@/lib/api-client";
import type { Note } from "@/lib/types";

export default function NotebookNotesPage() {
  const params = useParams<{ notebookId: string }>();
  const notebookId = params.notebookId;
  const queryClient = useQueryClient();

  const { data, isPending } = useQuery({
    queryKey: ["notebooks", notebookId, "notes"],
    queryFn: () => listNotes(notebookId),
  });

  const createMutation = useMutation({
    mutationFn: () => createNote(notebookId, { title: "Untitled note", content: "" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notebooks", notebookId, "notes"] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link href={`/notebooks/${notebookId}`} className="text-sm text-brand-600 hover:underline">
            ← Back to notebook
          </Link>
          <h1 className="mt-1 text-2xl font-semibold">Notes</h1>
        </div>
        <button
          onClick={() => createMutation.mutate()}
          disabled={createMutation.isPending}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          New note
        </button>
      </div>

      {isPending && <p className="text-sm text-slate-500">Loading...</p>}
      {data && data.items.length === 0 && (
        <p className="text-sm text-slate-500">No notes yet. Create one above.</p>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {data?.items.map((note) => (
          <NoteCard key={note.id} notebookId={notebookId} note={note} />
        ))}
      </div>
    </div>
  );
}

function NoteCard({ notebookId, note }: { notebookId: string; note: Note }) {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(note.title);
  const [content, setContent] = useState(note.content);
  const [dirty, setDirty] = useState(false);

  const saveMutation = useMutation({
    mutationFn: () => updateNote(notebookId, note.id, { title, content }),
    onSuccess: () => {
      setDirty(false);
      queryClient.invalidateQueries({ queryKey: ["notebooks", notebookId, "notes"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteNote(notebookId, note.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notebooks", notebookId, "notes"] }),
  });

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-white p-4">
      <input
        value={title}
        onChange={(e) => {
          setTitle(e.target.value);
          setDirty(true);
        }}
        className="border-b border-transparent bg-transparent font-medium focus:border-slate-300 focus:outline-none"
      />
      <textarea
        value={content}
        onChange={(e) => {
          setContent(e.target.value);
          setDirty(true);
        }}
        rows={6}
        placeholder="Write a note..."
        className="resize-none rounded-md border border-slate-200 p-2 text-sm focus:border-brand-500 focus:outline-none"
      />
      <div className="flex justify-between">
        <button
          onClick={() => deleteMutation.mutate()}
          disabled={deleteMutation.isPending}
          className="text-xs text-red-600 hover:underline disabled:opacity-50"
        >
          Delete
        </button>
        <button
          onClick={() => saveMutation.mutate()}
          disabled={!dirty || saveMutation.isPending}
          className="rounded-md bg-slate-100 px-3 py-1 text-xs font-medium hover:bg-slate-200 disabled:opacity-50"
        >
          {saveMutation.isPending ? "Saving..." : dirty ? "Save" : "Saved"}
        </button>
      </div>
    </div>
  );
}
