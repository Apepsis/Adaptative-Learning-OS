"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { getDueFlashcards, reviewFlashcard } from "@/lib/api-client";
import type { FlashcardRating } from "@/lib/types";

const RATING_BUTTONS: { rating: FlashcardRating; label: string; className: string }[] = [
  { rating: "again", label: "Again", className: "bg-red-50 text-red-700 hover:bg-red-100" },
  { rating: "hard", label: "Hard", className: "bg-amber-50 text-amber-700 hover:bg-amber-100" },
  { rating: "good", label: "Good", className: "bg-emerald-50 text-emerald-700 hover:bg-emerald-100" },
  { rating: "easy", label: "Easy", className: "bg-brand-50 text-brand-700 hover:bg-brand-100" },
];

export default function FlashcardReviewPage() {
  const params = useParams<{ subjectId: string }>();
  const subjectId = params.subjectId;
  const queryClient = useQueryClient();

  const { data, isPending } = useQuery({
    queryKey: ["subjects", subjectId, "flashcards", "due"],
    queryFn: () => getDueFlashcards(subjectId),
  });

  const [revealed, setRevealed] = useState(false);
  const [startedAt, setStartedAt] = useState(Date.now());
  const currentCard = data?.items[0];

  useEffect(() => {
    setRevealed(false);
    setStartedAt(Date.now());
  }, [currentCard?.id]);

  const reviewMutation = useMutation({
    mutationFn: (rating: FlashcardRating) =>
      reviewFlashcard(subjectId, currentCard!.id, { rating, response_ms: Date.now() - startedAt }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["subjects", subjectId, "flashcards", "due"] }),
  });

  return (
    <div className="max-w-xl space-y-6">
      <Link href={`/subjects/${subjectId}/flashcards`} className="text-sm text-brand-600 hover:underline">
        ← Back to flashcards
      </Link>
      <h1 className="text-2xl font-semibold">Review</h1>

      {isPending && <p className="text-sm text-slate-500">Loading...</p>}

      {data && data.items.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-600">
          Nothing due right now. Come back later, or generate more flashcards from your concepts.
        </div>
      )}

      {currentCard && (
        <div className="space-y-4">
          <p className="text-xs text-slate-500">{data!.items.length} card(s) due</p>
          <div className="rounded-lg border border-slate-200 bg-white p-6">
            <span className="mb-2 block text-[11px] uppercase tracking-wide text-slate-400">
              {revealed ? "Answer" : "Question"}
            </span>
            <p className="text-base">{revealed ? currentCard.back : currentCard.front}</p>
          </div>

          {!revealed && (
            <button
              onClick={() => setRevealed(true)}
              className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
            >
              Show answer
            </button>
          )}

          {revealed && (
            <div className="flex flex-wrap gap-2">
              {RATING_BUTTONS.map(({ rating, label, className }) => (
                <button
                  key={rating}
                  onClick={() => reviewMutation.mutate(rating)}
                  disabled={reviewMutation.isPending}
                  className={`rounded-md px-4 py-2 text-sm font-medium disabled:opacity-50 ${className}`}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
          {reviewMutation.isError && (
            <p className="text-sm text-red-600">{reviewMutation.error.message}</p>
          )}
        </div>
      )}
    </div>
  );
}
