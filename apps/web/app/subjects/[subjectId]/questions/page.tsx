"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import {
  createPracticeSession,
  createQuestion,
  generateQuestions,
  listConcepts,
  listQuestions,
} from "@/lib/api-client";
import type { QuestionType } from "@/lib/types";

const VERIFICATION_STYLES: Record<string, string> = {
  verified: "bg-emerald-100 text-emerald-800",
  unverified: "bg-slate-200 text-slate-600",
  quarantined: "bg-red-100 text-red-800",
};

export default function QuestionsPage() {
  const params = useParams<{ subjectId: string }>();
  const subjectId = params.subjectId;
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: questions, isPending } = useQuery({
    queryKey: ["subjects", subjectId, "questions"],
    queryFn: () => listQuestions(subjectId),
  });
  const { data: concepts } = useQuery({
    queryKey: ["subjects", subjectId, "concepts"],
    queryFn: () => listConcepts(subjectId),
  });

  const startMutation = useMutation({
    mutationFn: () => createPracticeSession(subjectId, { question_count: 10 }),
    onSuccess: (result) => router.push(`/subjects/${subjectId}/practice/${result.session.id}`),
  });

  return (
    <div className="max-w-3xl space-y-6">
      <Link href={`/subjects/${subjectId}`} className="text-sm text-brand-600 hover:underline">
        ← Back to subject
      </Link>

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Question bank</h1>
        <button
          onClick={() => startMutation.mutate()}
          disabled={startMutation.isPending}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {startMutation.isPending ? "Starting..." : "Start practice session"}
        </button>
      </div>
      {startMutation.isError && <p className="text-sm text-red-600">{startMutation.error.message}</p>}

      <GenerateForm subjectId={subjectId} concepts={concepts?.items ?? []} />
      <ManualCreateForm subjectId={subjectId} concepts={concepts?.items ?? []} />

      {isPending && <p className="text-sm text-slate-500">Loading...</p>}
      {questions && questions.items.length === 0 && (
        <p className="text-sm text-slate-500">No questions yet. Generate or add some above.</p>
      )}

      <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
        {questions?.items.map((q) => (
          <li key={q.id} className="flex items-center justify-between gap-3 p-4">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{q.stem}</p>
              <p className="mt-0.5 text-xs text-slate-500">
                {q.question_type} · {q.origin}
              </p>
            </div>
            <span
              className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${VERIFICATION_STYLES[q.verification_state] ?? ""}`}
            >
              {q.verification_state}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function GenerateForm({
  subjectId,
  concepts,
}: {
  subjectId: string;
  concepts: { id: string; canonical_name: string }[];
}) {
  const queryClient = useQueryClient();
  const [conceptId, setConceptId] = useState("");
  const [type, setType] = useState<QuestionType>("mcq");
  const [count, setCount] = useState(3);

  const mutation = useMutation({
    mutationFn: () => generateQuestions(subjectId, { concept_id: conceptId, question_type: type, count }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["subjects", subjectId, "questions"] }),
  });

  if (concepts.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        Build the curriculum first to generate questions grounded in your concepts.
      </p>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="mb-2 text-sm font-semibold text-slate-700">Generate from a concept</h2>
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={conceptId}
          onChange={(e) => setConceptId(e.target.value)}
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        >
          <option value="">Choose a concept...</option>
          {concepts.map((c) => (
            <option key={c.id} value={c.id}>
              {c.canonical_name}
            </option>
          ))}
        </select>
        <select
          value={type}
          onChange={(e) => setType(e.target.value as QuestionType)}
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        >
          <option value="mcq">Multiple choice</option>
          <option value="numeric">Numeric</option>
          <option value="short_answer">Short answer</option>
        </select>
        <input
          type="number"
          min={1}
          max={10}
          value={count}
          onChange={(e) => setCount(Number(e.target.value))}
          className="w-16 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        />
        <button
          onClick={() => conceptId && mutation.mutate()}
          disabled={!conceptId || mutation.isPending}
          className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {mutation.isPending ? "Generating..." : "Generate"}
        </button>
      </div>
      {mutation.isError && <p className="mt-2 text-sm text-red-600">{mutation.error.message}</p>}
    </div>
  );
}

function ManualCreateForm({
  subjectId,
  concepts,
}: {
  subjectId: string;
  concepts: { id: string; canonical_name: string }[];
}) {
  const queryClient = useQueryClient();
  const [type, setType] = useState<QuestionType>("mcq");
  const [stem, setStem] = useState("");
  const [options, setOptions] = useState(["", "", "", ""]);
  const [correctIndex, setCorrectIndex] = useState(0);
  const [numericAnswer, setNumericAnswer] = useState("");
  const [numericTolerance, setNumericTolerance] = useState("0");
  const [sampleAnswer, setSampleAnswer] = useState("");

  const mutation = useMutation({
    mutationFn: () => {
      const optionIds = ["a", "b", "c", "d"];
      if (type === "mcq") {
        return createQuestion(subjectId, {
          question_type: "mcq",
          stem,
          options: options.map((text, i) => ({ id: optionIds[i], text })),
          correct_option_id: optionIds[correctIndex],
        });
      }
      if (type === "numeric") {
        return createQuestion(subjectId, {
          question_type: "numeric",
          stem,
          numeric_answer: Number(numericAnswer),
          numeric_tolerance: Number(numericTolerance),
        });
      }
      return createQuestion(subjectId, { question_type: "short_answer", stem, sample_answer: sampleAnswer });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subjects", subjectId, "questions"] });
      setStem("");
      setOptions(["", "", "", ""]);
      setNumericAnswer("");
      setSampleAnswer("");
    },
  });

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="mb-2 text-sm font-semibold text-slate-700">Add a question manually</h2>
      <div className="space-y-2">
        <select
          value={type}
          onChange={(e) => setType(e.target.value as QuestionType)}
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        >
          <option value="mcq">Multiple choice</option>
          <option value="numeric">Numeric</option>
          <option value="short_answer">Short answer</option>
        </select>
        <textarea
          value={stem}
          onChange={(e) => setStem(e.target.value)}
          placeholder="Question stem"
          rows={2}
          className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        />

        {type === "mcq" &&
          options.map((option, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                type="radio"
                checked={correctIndex === i}
                onChange={() => setCorrectIndex(i)}
                aria-label={`Option ${i + 1} is correct`}
              />
              <input
                value={option}
                onChange={(e) => {
                  const next = [...options];
                  next[i] = e.target.value;
                  setOptions(next);
                }}
                placeholder={`Option ${i + 1}`}
                className="flex-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              />
            </div>
          ))}

        {type === "numeric" && (
          <div className="flex gap-2">
            <input
              value={numericAnswer}
              onChange={(e) => setNumericAnswer(e.target.value)}
              placeholder="Correct value"
              className="flex-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
            />
            <input
              value={numericTolerance}
              onChange={(e) => setNumericTolerance(e.target.value)}
              placeholder="Tolerance"
              className="w-24 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
            />
          </div>
        )}

        {type === "short_answer" && (
          <textarea
            value={sampleAnswer}
            onChange={(e) => setSampleAnswer(e.target.value)}
            placeholder="Reference answer"
            rows={2}
            className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        )}

        <button
          onClick={() => stem.trim() && mutation.mutate()}
          disabled={!stem.trim() || mutation.isPending}
          className="rounded-md bg-slate-100 px-3 py-1.5 text-sm font-medium hover:bg-slate-200 disabled:opacity-50"
        >
          Add question
        </button>
        {mutation.isError && <p className="text-sm text-red-600">{mutation.error.message}</p>}
      </div>
    </div>
  );
}
