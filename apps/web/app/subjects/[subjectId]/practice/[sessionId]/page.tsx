"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { getCurrentPracticeQuestion, getHint, submitAttempt } from "@/lib/api-client";
import type { AttemptResult } from "@/lib/types";

export default function PracticeSessionPage() {
  const params = useParams<{ subjectId: string; sessionId: string }>();
  const { subjectId, sessionId } = params;
  const queryClient = useQueryClient();

  const { data, isPending } = useQuery({
    queryKey: ["subjects", subjectId, "practice", sessionId],
    queryFn: () => getCurrentPracticeQuestion(subjectId, sessionId),
  });

  const [answer, setAnswer] = useState<string>("");
  const [hintsRevealed, setHintsRevealed] = useState<string[]>([]);
  const [startedAt, setStartedAt] = useState(Date.now());
  const [result, setResult] = useState<AttemptResult | null>(null);

  const questionId = data?.question?.id;

  useEffect(() => {
    setAnswer("");
    setHintsRevealed([]);
    setStartedAt(Date.now());
    setResult(null);
  }, [questionId]);

  const hintMutation = useMutation({
    mutationFn: () => getHint(subjectId, questionId!, hintsRevealed.length),
    onSuccess: (hint) => {
      if (hint.hint_text) setHintsRevealed((prev) => [...prev, hint.hint_text!]);
    },
  });

  const submitMutation = useMutation({
    mutationFn: () =>
      submitAttempt({
        question_id: questionId!,
        session_id: sessionId,
        raw_answer: buildRawAnswer(data!.question!.question_type, answer),
        elapsed_ms: Date.now() - startedAt,
        hints_used: hintsRevealed.length,
      }),
    onSuccess: (attemptResult) => setResult(attemptResult),
  });

  const nextMutation = useMutation({
    mutationFn: () => getCurrentPracticeQuestion(subjectId, sessionId),
    onSuccess: (next) => {
      queryClient.setQueryData(["subjects", subjectId, "practice", sessionId], next);
    },
  });

  if (isPending) return <p className="text-sm text-slate-500">Loading...</p>;
  if (!data) return <p className="text-sm text-red-600">Session not found.</p>;

  const { session, question } = data;

  if (!question) {
    return (
      <div className="max-w-xl space-y-4">
        <h1 className="text-2xl font-semibold">Session complete 🎉</h1>
        <p className="text-slate-600">
          You answered {session.total_questions} question{session.total_questions === 1 ? "" : "s"}.
        </p>
        <Link href={`/subjects/${subjectId}/questions`} className="text-brand-600 hover:underline">
          Back to question bank
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-xl space-y-4">
      <div className="flex items-center justify-between text-sm text-slate-500">
        <Link href={`/subjects/${subjectId}/questions`} className="text-brand-600 hover:underline">
          ← Exit
        </Link>
        <span>
          Question {session.current_index + 1} of {session.total_questions}
        </span>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-5">
        <p className="font-medium">{question.stem}</p>

        {!result && (
          <div className="mt-4 space-y-3">
            <AnswerInput
              questionType={question.question_type}
              options={question.options}
              units={question.units}
              value={answer}
              onChange={setAnswer}
            />

            {hintsRevealed.map((hint, i) => (
              <p key={i} className="rounded-md bg-amber-50 p-2 text-sm text-amber-800">
                Hint {i + 1}: {hint}
              </p>
            ))}

            <div className="flex gap-2">
              {hintsRevealed.length < question.hint_count && (
                <button
                  onClick={() => hintMutation.mutate()}
                  disabled={hintMutation.isPending}
                  className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium hover:bg-slate-50"
                >
                  Show hint ({question.hint_count - hintsRevealed.length} left)
                </button>
              )}
              <button
                onClick={() => submitMutation.mutate()}
                disabled={!answer.trim() || submitMutation.isPending}
                className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              >
                {submitMutation.isPending ? "Checking..." : "Submit"}
              </button>
            </div>
            {submitMutation.isError && (
              <p className="text-sm text-red-600">{submitMutation.error.message}</p>
            )}
          </div>
        )}

        {result && (
          <div className="mt-4 space-y-3 border-t border-slate-200 pt-4">
            <ResultBanner result={result} />
            {result.feedback && <p className="text-sm text-slate-700">{result.feedback}</p>}
            {result.solution_text && (
              <p className="text-sm text-slate-600">
                <span className="font-medium">Solution: </span>
                {result.solution_text}
              </p>
            )}
            {result.errors.map((error, i) => (
              <p key={i} className="text-sm text-slate-500">
                Likely issue: <span className="font-medium">{error.error_type}</span> — {error.explanation}
              </p>
            ))}
            <button
              onClick={() => nextMutation.mutate()}
              disabled={nextMutation.isPending}
              className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              Next question
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function buildRawAnswer(questionType: string, value: string): Record<string, unknown> {
  if (questionType === "mcq") return { option_id: value };
  if (questionType === "numeric") return { value: Number(value) };
  return { text: value };
}

function AnswerInput({
  questionType,
  options,
  units,
  value,
  onChange,
}: {
  questionType: string;
  options: { id: string; text: string }[] | null;
  units: string | null;
  value: string;
  onChange: (value: string) => void;
}) {
  if (questionType === "mcq") {
    return (
      <div className="space-y-2">
        {options?.map((option) => (
          <label key={option.id} className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              name="mcq-option"
              checked={value === option.id}
              onChange={() => onChange(option.id)}
            />
            {option.text}
          </label>
        ))}
      </div>
    );
  }
  if (questionType === "numeric") {
    return (
      <div className="flex items-center gap-2">
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-40 rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        {units && <span className="text-sm text-slate-500">{units}</span>}
      </div>
    );
  }
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      rows={3}
      placeholder="Your answer..."
      className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
    />
  );
}

function ResultBanner({ result }: { result: AttemptResult }) {
  const styles: Record<string, string> = {
    correct: "bg-emerald-50 text-emerald-800",
    partial: "bg-amber-50 text-amber-800",
    incorrect: "bg-red-50 text-red-800",
  };
  const labels: Record<string, string> = {
    correct: "Correct!",
    partial: "Partially correct",
    incorrect: "Not quite",
  };
  return (
    <div className={`rounded-md p-3 text-sm font-medium ${styles[result.correctness]}`}>
      {labels[result.correctness]} ({Math.round((result.score / result.max_score) * 100)}%)
    </div>
  );
}
