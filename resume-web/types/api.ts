export type Provider = "openai" | "anthropic" | "gemini";

export interface Bullet { id?: string; text: string; skills: string[] }
export interface Experience {
  id?: string; company: string; role: string; start_date: string; end_date: string | null; bullets: Bullet[];
}
export interface Education { institution: string; degree: string; field: string; start_date: string; end_date: string | null }
export interface Skills {
  languages: string[];
  frontend: string[];
  mobile: string[];
  backend: string[];
  databases: string[];
  cloud_devops: string[];
  tools: string[];
  frameworks?: string[];
  soft: string[];
}
export interface Project {
  id?: string;
  name: string;
  url?: string;
  skills?: string[];
  bullets: Bullet[];
}
export interface Profile {
  full_name: string; email: string; phone: string; location: string;
  linkedin: string; github: string; portfolio: string;
  experience: Experience[]; projects: Project[]; education: Education[]; certifications: string[]; skills: Skills;
}
export interface ImportResponse { message: string; profile: Profile }

export interface ApiKey {
  id: string; provider: Provider; label: string; is_active: boolean; key_hint: string; created_at: string;
}
export interface NewApiKey { provider: Provider; api_key: string; raw_key?: string; label: string }
export interface ModelsResponse {
  providers?: Partial<Record<Provider, string[]>>;
  platform_defaults?: string[];
  provider?: string;
  fast_models?: string[];
  strong_models?: string[];
}

export interface GenerateRequest {
  job_description: string; selected_key_id: string | null; model: string; custom_instructions: string;
}
export interface BulletRecommendation { original: string; suggested: string; reason?: string }
export interface ResumeResult {
  id: string;
  markdown: string;
  ats_score: number;
  matched_keywords: string[];
  missing_keywords: string[];
  recommendations: BulletRecommendation[];
  created_at?: string;
  company?: string;
  job_title?: string;
  has_docx?: boolean;
  has_pdf?: boolean;
  download_docx_url?: string | null;
  download_pdf_url?: string | null;
  job_description?: string;
  jd_text?: string;
  notes?: string[] | string;
}

export interface HistoryItem {
  id: string;
  jd_title?: string | null;
  jd_company?: string | null;
  job_title?: string | null;
  company?: string | null;
  ats_score?: number | null;
  model_used?: string | null;
  provider_used?: string | null;
  has_docx: boolean;
  has_pdf: boolean;
  download_docx_url?: string | null;
  download_pdf_url?: string | null;
  created_at: string;
  markdown?: string;
}

export interface HistoryListResponse {
  items: HistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface HistoryDetail extends HistoryItem {
  jd_text?: string;
  notes?: string | null;
}

export interface DownloadUrlsResponse {
  download_docx_url: string | null;
  download_pdf_url: string | null;
  has_docx?: boolean;
  has_pdf?: boolean;
}

export interface APIError { detail: string; errors?: string[] }

export interface User {
  id: string;
  name: string;
  email: string;
  is_active: boolean;
  created_at?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  name: string;
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  user?: User;
}
