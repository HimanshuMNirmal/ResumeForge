export type Provider = "openai" | "anthropic" | "gemini";

export interface Bullet { text: string; skills: string[] }
export interface Experience {
  company: string; role: string; start_date: string; end_date: string | null; bullets: Bullet[];
}
export interface Education { institution: string; degree: string; field: string; start_date: string; end_date: string | null }
export interface Skills { languages: string[]; frameworks: string[]; tools: string[]; soft: string[] }
export interface Profile {
  full_name: string; email: string; phone: string; location: string;
  linkedin: string; github: string; portfolio: string;
  experience: Experience[]; education: Education[]; certifications: string[]; skills: Skills;
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
  id: string; markdown: string; ats_score: number;
  matched_keywords: string[]; missing_keywords: string[];
  recommendations: BulletRecommendation[]; created_at?: string; company?: string; job_title?: string;
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
