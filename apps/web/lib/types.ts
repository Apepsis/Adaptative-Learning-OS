export type SourceStatus = "UPLOADED" | "QUEUED" | "FAILED";

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
