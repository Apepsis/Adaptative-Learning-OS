import type {
  BuildCurriculumResponse,
  ChatMessage,
  ChatMessageListResponse,
  Concept,
  ConceptDetail,
  ConceptListResponse,
  HealthReadyResponse,
  Note,
  NoteListResponse,
  Notebook,
  NotebookListResponse,
  NotebookSourceListResponse,
  SearchResponse,
  Source,
  SourceListResponse,
  SourceStatusResponse,
  Subject,
  SubjectListResponse,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    return JSON.stringify(body.detail ?? body);
  } catch {
    return response.statusText;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) {
    throw new ApiError(response.status, await parseErrorDetail(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function getHealthReady(): Promise<HealthReadyResponse> {
  return request<HealthReadyResponse>("/health/ready");
}

export function listSubjects(): Promise<SubjectListResponse> {
  return request<SubjectListResponse>("/v1/subjects");
}

export function createSubject(data: { name: string; subject_type?: string }): Promise<Subject> {
  return request<Subject>("/v1/subjects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function getSubject(subjectId: string): Promise<Subject> {
  return request<Subject>(`/v1/subjects/${subjectId}`);
}

export function listSources(subjectId?: string): Promise<SourceListResponse> {
  const query = subjectId ? `?subject_id=${encodeURIComponent(subjectId)}` : "";
  return request<SourceListResponse>(`/v1/sources${query}`);
}

export function getSource(sourceId: string): Promise<Source> {
  return request<Source>(`/v1/sources/${sourceId}`);
}

export function getSourceStatus(sourceId: string): Promise<SourceStatusResponse> {
  return request<SourceStatusResponse>(`/v1/sources/${sourceId}/status`);
}

export interface UploadSourceInput {
  file: File;
  title?: string;
  subjectId?: string;
  sourceRole?: string;
}

export function uploadSource({ file, title, subjectId, sourceRole }: UploadSourceInput): Promise<Source> {
  const formData = new FormData();
  formData.append("file", file);
  if (title) formData.append("title", title);
  if (subjectId) formData.append("subject_id", subjectId);
  if (sourceRole) formData.append("source_role", sourceRole);

  return request<Source>("/v1/sources/upload", { method: "POST", body: formData });
}

export function reprocessSource(sourceId: string): Promise<Source> {
  return request<Source>(`/v1/sources/${sourceId}/reprocess`, { method: "POST" });
}

export function deleteSource(sourceId: string): Promise<void> {
  return request<void>(`/v1/sources/${sourceId}`, { method: "DELETE" });
}

export interface SearchInput {
  query: string;
  subjectId?: string;
  sourceIds?: string[];
  topK?: number;
}

export function search({ query, subjectId, sourceIds, topK }: SearchInput): Promise<SearchResponse> {
  return request<SearchResponse>("/v1/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      subject_id: subjectId,
      source_ids: sourceIds,
      top_k: topK,
    }),
  });
}

const JSON_HEADERS = { "Content-Type": "application/json" };

export function listNotebooks(): Promise<NotebookListResponse> {
  return request<NotebookListResponse>("/v1/notebooks");
}

export function createNotebook(data: { title: string; description?: string }): Promise<Notebook> {
  return request<Notebook>("/v1/notebooks", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(data),
  });
}

export function getNotebook(notebookId: string): Promise<Notebook> {
  return request<Notebook>(`/v1/notebooks/${notebookId}`);
}

export function deleteNotebook(notebookId: string): Promise<void> {
  return request<void>(`/v1/notebooks/${notebookId}`, { method: "DELETE" });
}

export function listNotebookSources(notebookId: string): Promise<NotebookSourceListResponse> {
  return request<NotebookSourceListResponse>(`/v1/notebooks/${notebookId}/sources`);
}

export function addNotebookSource(notebookId: string, sourceId: string): Promise<void> {
  return request<void>(`/v1/notebooks/${notebookId}/sources`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ source_id: sourceId }),
  });
}

export function removeNotebookSource(notebookId: string, sourceId: string): Promise<void> {
  return request<void>(`/v1/notebooks/${notebookId}/sources/${sourceId}`, { method: "DELETE" });
}

export function listNotes(notebookId: string): Promise<NoteListResponse> {
  return request<NoteListResponse>(`/v1/notebooks/${notebookId}/notes`);
}

export function createNote(
  notebookId: string,
  data: { title?: string; content?: string },
): Promise<Note> {
  return request<Note>(`/v1/notebooks/${notebookId}/notes`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(data),
  });
}

export function updateNote(
  notebookId: string,
  noteId: string,
  data: { title?: string; content?: string },
): Promise<Note> {
  return request<Note>(`/v1/notebooks/${notebookId}/notes/${noteId}`, {
    method: "PATCH",
    headers: JSON_HEADERS,
    body: JSON.stringify(data),
  });
}

export function deleteNote(notebookId: string, noteId: string): Promise<void> {
  return request<void>(`/v1/notebooks/${notebookId}/notes/${noteId}`, { method: "DELETE" });
}

export function listMessages(notebookId: string): Promise<ChatMessageListResponse> {
  return request<ChatMessageListResponse>(`/v1/notebooks/${notebookId}/messages`);
}

export function sendChatMessage(notebookId: string, message: string): Promise<ChatMessage> {
  return request<ChatMessage>(`/v1/notebooks/${notebookId}/chat`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ message }),
  });
}

export function buildCurriculum(subjectId: string): Promise<BuildCurriculumResponse> {
  return request<BuildCurriculumResponse>(`/v1/subjects/${subjectId}/curriculum/build`, {
    method: "POST",
  });
}

export function listConcepts(subjectId: string): Promise<ConceptListResponse> {
  return request<ConceptListResponse>(`/v1/subjects/${subjectId}/concepts`);
}

export function getConcept(subjectId: string, conceptId: string): Promise<ConceptDetail> {
  return request<ConceptDetail>(`/v1/subjects/${subjectId}/concepts/${conceptId}`);
}

export function updateConcept(
  subjectId: string,
  conceptId: string,
  data: { canonical_name?: string; definition?: string; status?: string },
): Promise<Concept> {
  return request<Concept>(`/v1/subjects/${subjectId}/concepts/${conceptId}`, {
    method: "PATCH",
    headers: JSON_HEADERS,
    body: JSON.stringify(data),
  });
}

export function deleteConcept(subjectId: string, conceptId: string): Promise<void> {
  return request<void>(`/v1/subjects/${subjectId}/concepts/${conceptId}`, { method: "DELETE" });
}

export function mergeConcepts(
  subjectId: string,
  primaryConceptId: string,
  absorbConceptId: string,
): Promise<Concept> {
  return request<Concept>(`/v1/subjects/${subjectId}/concepts/${primaryConceptId}/merge`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ absorb_concept_id: absorbConceptId }),
  });
}
