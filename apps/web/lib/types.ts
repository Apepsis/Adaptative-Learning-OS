export type SourceStatus = "UPLOADED" | "PARSING" | "READY" | "FAILED" | "UNSUPPORTED";

export interface Subject {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  subject_type: string | null;
  color_token: string | null;
  created_at: string;
}

export interface SubjectListResponse {
  items: Subject[];
  total: number;
}

export interface Source {
  id: string;
  subject_id: string | null;
  type: string;
  title: string;
  original_filename: string | null;
  mime_type: string;
  size_bytes: number;
  status: SourceStatus;
  error_message: string | null;
  source_role: string | null;
  created_at: string;
  updated_at: string;
}

export interface SourceListResponse {
  items: Source[];
  total: number;
}

export interface SourceStatusResponse {
  id: string;
  status: SourceStatus;
  error_message: string | null;
  updated_at: string;
}

export interface HealthReadyResponse {
  status: string;
  database?: string;
  redis?: string;
  object_storage?: string;
}

export interface SearchResult {
  chunk_id: string;
  source_id: string;
  source_title: string;
  heading_path: string[];
  page_start: number;
  page_end: number;
  text: string;
  score: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  not_found: boolean;
}

export interface Notebook {
  id: string;
  title: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface NotebookListResponse {
  items: Notebook[];
  total: number;
}

export interface NotebookSource {
  source_id: string;
  title: string;
  status: SourceStatus;
  added_at: string;
}

export interface NotebookSourceListResponse {
  items: NotebookSource[];
}

export interface Note {
  id: string;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface NoteListResponse {
  items: Note[];
}

export interface ChatCitation {
  chunk_id: string;
  source_id: string;
  source_title: string;
  page_start: number;
  page_end: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: ChatCitation[];
  not_found: boolean;
  created_at: string;
}

export interface ChatMessageListResponse {
  items: ChatMessage[];
}
