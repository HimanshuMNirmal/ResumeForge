import type {
  ApiKey,
  AuthResponse,
  GenerateRequest,
  ImportResponse,
  LoginRequest,
  ModelsResponse,
  NewApiKey,
  Profile,
  RegisterRequest,
  ResumeResult,
  User,
} from "@/types/api";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "resumeforge_token";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

type TokenProvider = () => string | null | Promise<string | null>;
let tokenProvider: TokenProvider = () => getStoredToken();

/** Wire this to an external token provider if desired */
export const setTokenProvider = (fn: TokenProvider) => {
  tokenProvider = fn;
};

export class ApiError extends Error {
  constructor(public status: number, message: string, public body?: unknown) {
    super(message);
    this.name = "ApiError";
  }
}

export class ImportValidationError extends ApiError {
  constructor(message: string, public errors: string[]) {
    super(422, message);
    this.name = "ImportValidationError";
  }
}

async function toError(res: Response): Promise<ApiError> {
  let body: any = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON body */
  }
  if (res.status === 422) {
    if (Array.isArray(body?.errors)) {
      return new ImportValidationError(body.detail ?? "Validation failed", body.errors);
    }
    if (Array.isArray(body?.detail)) {
      return new ImportValidationError(
        "Validation failed",
        body.detail.map((d: any) => `${(d.loc ?? []).slice(1).join(".")}: ${d.msg}`)
      );
    }
  }
  const msg = typeof body?.detail === "string" ? body.detail : res.statusText || "Request failed";
  return new ApiError(res.status, msg, body);
}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = await tokenProvider();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers,
      credentials: "include", // send cookies for refresh token
    });
  } catch {
    throw new ApiError(0, "Can't reach the server. Check your connection and try again.");
  }
  if (!res.ok) throw await toError(res);
  return res;
}

const json = async <T,>(path: string, init?: RequestInit) =>
  (await request(path, init)).json() as Promise<T>;

async function download(path: string, filename: string) {
  const blob = await (await request(path)).blob();
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  a.click();
  URL.revokeObjectURL(url);
}

export const api = {
  auth: {
    login: async (creds: LoginRequest) => {
      const data = await json<{ access_token: string }>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify(creds),
      });
      setStoredToken(data.access_token);
      return data;
    },
    register: async (creds: RegisterRequest) => {
      const data = await json<{ access_token: string; user: User }>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify(creds),
      });
      setStoredToken(data.access_token);
      return data;
    },
    me: () => json<User>("/api/v1/auth/me"),
    refresh: async () => {
      const data = await json<{ access_token: string }>("/api/v1/auth/refresh", {
        method: "POST",
      });
      setStoredToken(data.access_token);
      return data;
    },
    logout: async () => {
      try {
        await request("/api/v1/auth/logout", { method: "POST" });
      } finally {
        setStoredToken(null);
      }
    },
  },
  profile: {
    get: () => json<Profile>("/api/v1/profile"),
    update: (p: Profile) =>
      json<Profile>("/api/v1/profile", { method: "PUT", body: JSON.stringify(p) }),
    export: () => download("/api/v1/profile/export", "resume_profile.json"),
    sample: () => download("/api/v1/profile/sample", "sample_resume_profile.json"),
    import: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return json<ImportResponse>("/api/v1/profile/import", { method: "POST", body: fd });
    },
  },
  keys: {
    list: () => json<ApiKey[]>("/api/v1/keys"),
    add: (k: NewApiKey) =>
      json<ApiKey>("/api/v1/keys", { method: "POST", body: JSON.stringify(k) }),
    remove: (id: string) => request(`/api/v1/keys/${id}`, { method: "DELETE" }),
    toggle: (id: string) => json<ApiKey>(`/api/v1/keys/${id}/toggle`, { method: "PATCH" }),
    models: () => json<ModelsResponse>("/api/v1/keys/models"),
  },
  resume: {
    generate: (b: GenerateRequest) =>
      json<ResumeResult>("/api/v1/resume/generate", { method: "POST", body: JSON.stringify(b) }),
    history: () => json<ResumeResult[]>("/api/v1/resume/history"),
    get: (id: string) => json<ResumeResult>(`/api/v1/resume/history/${id}`),
  },
};
