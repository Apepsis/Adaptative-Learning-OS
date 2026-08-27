"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { deleteFlashcard, generateFlashcards, listFlashcards } from "@/lib/api-client";
import type { Flashcard } from "@/lib/types";

export default function FlashcardsPage() {
  const params = useParams<{ subjectId: string }>();
  const subjectId = params.subjectId;
  const queryClient = useQueryClient();

  const { data, isPending } = useQuery({
    queryKey: ["subjects", subjectId, "flashcards"],
    queryFn: () => listFlashcards(subjectId),
  });

  const [result, setResult] = useState<string | null>(null);
  const generateMutation = useMutation({
    mutationFn: () => generateFlashcards(subjectId),
    onSuccess: (r) => {
      setResult(`${r.created} new flashcard${r.created === 1 ? "" : "s"} created.`);
      queryClient.invalidateQueries({ queryKey: ["subjects", subjectId, "flashcards"] });
    },
  });

  return (
    <div className="max-w-2xl space-y-6">
      <Link href={`/subjects/${subjectId}`} className="text-sm text-brand-600 hover:underline">
        ← Back to subject
      </Link>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Flashcards</h1>
        <div className="flex gap-2">
          <Link
            href={`/subjects/${subjectId}/flashcards/review`}
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50"
          >
            Review due cards
          </Link>
          <button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {generateMutation.isPending ? "Generating..." : "Generate from concepts"}
          </button>
        </div>
      </div>

      {result && <p className="text-sm text-emerald-700">{result}</p>}
      {isPending && <p className="text-sm text-slate-500">Loading...</p>}
      {data && data.items.length === 0 && (
        <p className="text-sm text-slate-500">
          No flashcards yet. Build the curriculum first, then generate flashcards above.
        </p>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {data?.items.map((card) => (
          <FlashcardTile key={card.id} subjectId={subjectId} card={card} />
        ))}
      </div>
    </div>
  );
}

function FlashcardTile({ subjectId, card }: { subjectId: string; card: Flashcard }) {
  const queryClient = useQueryClient();
  const [flipped, setFlipped] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => deleteFlashcard(subjectId, card.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["subjects", subjectId, "flashcards"] }),
  });

  return (
    <div className="flex flex-col justify-between rounded-lg border border-slate-200 bg-white p-4">
      <button onClick={() => setFlipped((v) => !v)} className="min-h-[4rem] text-left text-sm">
        <span className="mb-1 block text-[11px] uppercase tracking-wide text-slate-400">
          {flipped ? "Answer" : "Question"}
        </span>
        {flipped ? card.back : card.front}
      </button>
      <div className="mt-3 flex items-center justify-between">
        <button onClick={() => setFlipped((v) => !v)} className="text-xs text-brand-600 hover:underline">
          Flip
        </button>
        <button
          onClick={() => deleteMutation.mutate()}
          className="text-xs text-red-600 hover:underline"
        >
          Delete
        </button>
      </div>
    </div>
  );
}
