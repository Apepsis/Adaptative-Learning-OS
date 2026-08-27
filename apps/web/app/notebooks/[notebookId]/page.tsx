"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  addNotebookSource,
  getNotebook,
  listMessages,
  listNotebookSources,
  listSources,
  removeNotebookSource,
  sendChatMessage,
} from "@/lib/api-client";
import type { ChatMessage } from "@/lib/types";

export default function NotebookDetailPage() {
  const params = useParams<{ notebookId: string }>();
  const notebookId = params.notebookId;
  const queryClient = useQueryClient();

  const { data: notebook } = useQuery({
    queryKey: ["notebooks", notebookId],
    queryFn: () => getNotebook(notebookId),
  });

  const { data: activeSources } = useQuery({
    queryKey: ["notebooks", notebookId, "sources"],
    queryFn: () => listNotebookSources(notebookId),
  });

  const { data: allSources } = useQuery({ queryKey: ["sources"], queryFn: () => listSources() });

  const { data: messages } = useQuery({
    queryKey: ["notebooks", notebookId, "messages"],
    queryFn: () => listMessages(notebookId),
  });

  const [selectedSourceId, setSelectedSourceId] = useState("");

  const addSourceMutation = useMutation({
    mutationFn: (sourceId: string) => addNotebookSource(notebookId, sourceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notebooks", notebookId, "sources"] });
      setSelectedSourceId("");
    },
  });

  const removeSourceMutation = useMutation({
    mutationFn: (sourceId: string) => removeNotebookSource(notebookId, sourceId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notebooks", notebookId, "sources"] }),
  });

  const [draft, setDraft] = useState("");
  const chatMutation = useMutation({
    mutationFn: (message: string) => sendChatMessage(notebookId, message),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notebooks", notebookId, "messages"] });
      setDraft("");
    },
  });

  const activeSourceIds = new Set(activeSources?.items.map((s) => s.source_id));
  const availableToAdd = (allSources?.items ?? []).filter(
    (s) => s.status === "READY" && !activeSourceIds.has(s.id),
  );

  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages?.items.length]);

  const onSend = (event: React.FormEvent) => {
    event.preventDefault();
    if (!draft.trim() || chatMutation.isPending) return;
    chatMutation.mutate(draft);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{notebook?.title ?? "Notebook"}</h1>
        <Link href={`/notebooks/${notebookId}/notes`} className="text-sm text-brand-600 hover:underline">
          Notes →
        </Link>
      </div>

      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <aside className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-700">Active sources</h2>

          {activeSources?.items.length === 0 && (
            <p className="text-xs text-slate-500">
              No sources yet. Add one below — chat won&apos;t work without at least one.
            </p>
          )}

          <ul className="space-y-1.5">
            {activeSources?.items.map((source) => (
              <li
                key={source.source_id}
                className="flex items-center justify-between gap-2 rounded-md bg-slate-50 px-2 py-1.5 text-xs"
              >
                <Link href={`/library/${source.source_id}`} className="truncate hover:underline">
                  {source.title}
                </Link>
                <button
                  onClick={() => removeSourceMutation.mutate(source.source_id)}
                  className="shrink-0 text-slate-400 hover:text-red-600"
                  aria-label={`Remove ${source.title}`}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>

          <div className="flex gap-2 pt-2">
            <select
              value={selectedSourceId}
              onChange={(e) => setSelectedSourceId(e.target.value)}
              className="min-w-0 flex-1 rounded-md border border-slate-300 px-2 py-1.5 text-xs"
            >
              <option value="">Add a ready source...</option>
              {availableToAdd.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.title}
                </option>
              ))}
            </select>
            <button
              onClick={() => selectedSourceId && addSourceMutation.mutate(selectedSourceId)}
              disabled={!selectedSourceId || addSourceMutation.isPending}
              className="rounded-md bg-brand-600 px-2 py-1.5 text-xs font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              Add
            </button>
          </div>
          {availableToAdd.length === 0 && (
            <p className="text-xs text-slate-400">
              No other ready sources.{" "}
              <Link href="/library/upload" className="text-brand-600 hover:underline">
                Upload one
              </Link>
              .
            </p>
          )}
        </aside>

        <section className="flex h-[65vh] flex-col rounded-lg border border-slate-200 bg-white">
          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            {messages?.items.length === 0 && (
              <p className="text-sm text-slate-500">
                Ask something about the active sources above — every answer will say where it came
                from, or say plainly when it can&apos;t find an answer.
              </p>
            )}
            {messages?.items.map((message) => (
              <ChatBubble key={message.id} message={message} />
            ))}
            {chatMutation.isPending && (
              <div className="text-sm text-slate-400">Thinking...</div>
            )}
            {chatMutation.isError && (
              <p className="text-sm text-red-600">{chatMutation.error.message}</p>
            )}
            <div ref={scrollRef} />
          </div>

          <form onSubmit={onSend} className="flex gap-2 border-t border-slate-200 p-3">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Ask about your sources..."
              className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
            <button
              type="submit"
              disabled={!draft.trim() || chatMutation.isPending}
              className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              Send
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}

function ChatBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
          isUser ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-800"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.citations.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5 border-t border-slate-200 pt-2">
            {message.citations.map((citation, i) => (
              <Link
                key={citation.chunk_id}
                href={`/library/${citation.source_id}`}
                className="rounded bg-white px-1.5 py-0.5 text-[11px] text-brand-600 hover:underline"
                title={citation.source_title}
              >
                [{i + 1}] p.{citation.page_start}
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
