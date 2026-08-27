import type {
  AttemptResult,
  BuildCurriculumResponse,
  ChatMessage,
  ChatMessageListResponse,
  Concept,
  ConceptDetail,
  ConceptListResponse,
  ConceptMastery,
  ConceptMasteryListResponse,
  Flashcard,
  FlashcardDueListResponse,
  FlashcardListResponse,
  FlashcardRating,
  FlashcardReviewResult,
  GenerateFlashcardsResponse,
  GenerateQuestionsResponse,
  HealthReadyResponse,
  HintResponse,
  MisconceptionListResponse,
  Note,
  NoteListResponse,
  Notebook,
  NotebookListResponse,
  NotebookSourceListResponse,
  PracticeSessionCurrent,
  Question,
  QuestionListResponse,
  QuestionType,
  SearchResponse,
  Source,
  SourceListResponse,
  SourceStatusResponse,
  StudyGuide,
  Subject,
  SubjectListResponse,
  WeaknessListResponse,
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

export function generateFlashcards(subjectId: string): Promise<GenerateFlashcardsResponse> {
  return request<GenerateFlashcardsResponse>(`/v1/subjects/${subjectId}/flashcards/generate`, {
    method: "POST",
  });
}

export function listFlashcards(subjectId: string): Promise<FlashcardListResponse> {
  return request<FlashcardListResponse>(`/v1/subjects/${subjectId}/flashcards`);
}

export function createFlashcard(
  subjectId: string,
  data: { concept_id: string; front: string; back: string },
): Promise<Flashcard> {
  return request<Flashcard>(`/v1/subjects/${subjectId}/flashcards`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(data),
  });
}

export function deleteFlashcard(subjectId: string, flashcardId: string): Promise<void> {
  return request<void>(`/v1/subjects/${subjectId}/flashcards/${flashcardId}`, { method: "DELETE" });
}

export function generateStudyGuide(subjectId: string): Promise<StudyGuide> {
  return request<StudyGuide>(`/v1/subjects/${subjectId}/study-guide/generate`, { method: "POST" });
}

export function getStudyGuide(subjectId: string): Promise<StudyGuide> {
  return request<StudyGuide>(`/v1/subjects/${subjectId}/study-guide`);
}

export function listQuestions(subjectId: string): Promise<QuestionListResponse> {
  return request<QuestionListResponse>(`/v1/subjects/${subjectId}/questions`);
}

export interface CreateQuestionInput {
  concept_id?: string;
  question_type: QuestionType;
  stem: string;
  options?: { id: string; text: string }[];
  correct_option_id?: string;
  numeric_answer?: number;
  numeric_tolerance?: number;
  units?: string;
  sample_answer?: string;
  hints?: string[];
  solution_text?: string;
}

export function createQuestion(subjectId: string, data: CreateQuestionInput): Promise<Question> {
  return request<Question>(`/v1/subjects/${subjectId}/questions`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(data),
  });
}

export function generateQuestions(
  subjectId: string,
  data: { concept_id: string; question_type: QuestionType; count?: number },
): Promise<GenerateQuestionsResponse> {
  return request<GenerateQuestionsResponse>(`/v1/subjects/${subjectId}/questions/generate`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(data),
  });
}

export function getHint(subjectId: string, questionId: string, index: number): Promise<HintResponse> {
  return request<HintResponse>(`/v1/subjects/${subjectId}/questions/${questionId}/hints/${index}`);
}

export function createPracticeSession(
  subjectId: string,
  data: { concept_ids?: string[]; question_count?: number },
): Promise<PracticeSessionCurrent> {
  return request<PracticeSessionCurrent>(`/v1/subjects/${subjectId}/practice/sessions`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(data),
  });
}

export function getCurrentPracticeQuestion(
  subjectId: string,
  sessionId: string,
): Promise<PracticeSessionCurrent> {
  return request<PracticeSessionCurrent>(
    `/v1/subjects/${subjectId}/practice/sessions/${sessionId}/current`,
  );
}

export interface SubmitAttemptInput {
  question_id: string;
  session_id?: string;
  raw_answer: Record<string, unknown>;
  elapsed_ms?: number;
  hints_used?: number;
  solution_revealed?: boolean;
}

export function submitAttempt(data: SubmitAttemptInput): Promise<AttemptResult> {
  return request<AttemptResult>("/v1/attempts", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(data),
  });
}

export function getSubjectMastery(subjectId: string): Promise<ConceptMasteryListResponse> {
  return request<ConceptMasteryListResponse>(`/v1/subjects/${subjectId}/mastery`);
}

export function getConceptMastery(subjectId: string, conceptId: string): Promise<ConceptMastery> {
  return request<ConceptMastery>(`/v1/subjects/${subjectId}/mastery/concepts/${conceptId}`);
}

export function getWeaknesses(subjectId: string): Promise<WeaknessListResponse> {
  return request<WeaknessListResponse>(`/v1/subjects/${subjectId}/mastery/weaknesses`);
}

export function getMisconceptionPatterns(subjectId: string): Promise<MisconceptionListResponse> {
  return request<MisconceptionListResponse>(`/v1/subjects/${subjectId}/mastery/patterns`);
}

export function getDueFlashcards(subjectId: string): Promise<FlashcardDueListResponse> {
  return request<FlashcardDueListResponse>(`/v1/subjects/${subjectId}/flashcards/due`);
}

export function reviewFlashcard(
  subjectId: string,
  flashcardId: string,
  data: { rating: FlashcardRating; response_ms?: number },
): Promise<FlashcardReviewResult> {
  return request<FlashcardReviewResult>(`/v1/subjects/${subjectId}/flashcards/${flashcardId}/review`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(data),
  });
}
