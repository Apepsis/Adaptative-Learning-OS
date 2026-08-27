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

export type ConceptType = "topic" | "subtopic" | "concept" | "skill";
export type ConceptStatus = "PROPOSED" | "APPROVED" | "MERGED" | "REJECTED";

export interface Concept {
  id: string;
  canonical_name: string;
  slug: string;
  definition: string | null;
  concept_type: ConceptType;
  status: ConceptStatus;
  created_at: string;
}

export interface ConceptListResponse {
  items: Concept[];
  total: number;
}

export interface ConceptEdge {
  id: string;
  source_concept_id: string;
  target_concept_id: string;
  relation: string;
  confidence: number;
  provenance_type: string;
  approved: boolean;
}

export interface EvidenceExcerpt {
  chunk_id: string;
  source_id: string;
  source_title: string;
  page_start: number;
  page_end: number;
  text: string;
}

export interface ConceptDetail extends Concept {
  outgoing_edges: ConceptEdge[];
  incoming_edges: ConceptEdge[];
  evidence: EvidenceExcerpt[];
}

export interface BuildCurriculumResponse {
  concepts_created: number;
  concepts_updated: number;
  edges_created: number;
  edges_skipped_cycle: number;
  chunks_considered: number;
}

export interface Flashcard {
  id: string;
  concept_id: string;
  front: string;
  back: string;
  source_grounded: boolean;
  created_at: string;
}

export interface FlashcardListResponse {
  items: Flashcard[];
  total: number;
}

export interface GenerateFlashcardsResponse {
  created: number;
  skipped_existing: number;
}

export interface StudyGuide {
  subject_id: string;
  content: string;
  updated_at: string;
}

export type QuestionType = "mcq" | "numeric" | "short_answer";

export interface QuestionOption {
  id: string;
  text: string;
}

export interface Question {
  id: string;
  subject_id: string;
  concept_id: string | null;
  origin: string;
  question_type: QuestionType;
  stem: string;
  options: QuestionOption[] | null;
  correct_option_id: string | null;
  numeric_answer: number | null;
  numeric_tolerance: number | null;
  units: string | null;
  sample_answer: string | null;
  hints: string[] | null;
  solution_text: string | null;
  verification_state: string;
  created_at: string;
}

export interface QuestionListResponse {
  items: Question[];
  total: number;
}

export interface QuestionPracticeView {
  id: string;
  question_type: QuestionType;
  stem: string;
  options: QuestionOption[] | null;
  units: string | null;
  hint_count: number;
}

export interface GenerateQuestionsResponse {
  items: Question[];
}

export interface PracticeSessionInfo {
  id: string;
  subject_id: string;
  total_questions: number;
  current_index: number;
  completed_at: string | null;
}

export interface PracticeSessionCurrent {
  session: PracticeSessionInfo;
  question: QuestionPracticeView | null;
}

export interface AttemptErrorInfo {
  error_type: string;
  explanation: string;
}

export interface AttemptResult {
  id: string;
  correctness: "correct" | "partial" | "incorrect";
  score: number;
  max_score: number;
  feedback: string | null;
  correct_option_id: string | null;
  numeric_answer: number | null;
  sample_answer: string | null;
  solution_text: string | null;
  errors: AttemptErrorInfo[];
}

export interface HintResponse {
  hint_text: string | null;
  hints_used: number;
  hints_remaining: number;
}
