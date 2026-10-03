import type {
  ApiKey,
  AuthResponse,
  DownloadUrlsResponse,
  GenerateRequest,
  HistoryDetail,
  HistoryItem,
  HistoryListResponse,
  ImportResponse,
  LoginRequest,
  ModelsResponse,
  NewApiKey,
  Profile,
  RegisterRequest,
  ResumeResult,
  User,
} from "@/types/api";

export function getBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== "undefined") {
    // When running in browser on an HTTPS site (such as Vercel), avoid Mixed Content errors:
    // If NEXT_PUBLIC_API_URL is an insecure http:// endpoint or empty, use relative path ""
    // which delegates securely to Next.js API rewrites (same-origin HTTPS proxy).
    if (window.location.protocol === "https:" && (!envUrl || envUrl.startsWith("http://"))) {
      return "";
    }
  }
  return envUrl ?? "http://localhost:8000";
}

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

export interface ErrorDetail {
  field?: string;
  message: string;
}

export class ApiError extends Error {
  public errors: string[];
  public fieldErrors: Record<string, string>;

  constructor(
    public status: number,
    message: string,
    public code: string = "ERROR",
    public details: ErrorDetail[] = [],
    public body?: unknown
  ) {
    super(message);
    this.name = "ApiError";
    this.errors = details.map((d) => (d.field ? `${d.field}: ${d.message}` : d.message));
    if (this.errors.length === 0 && message) {
      this.errors = [message];
    }
    this.fieldErrors = {};
    for (const d of details) {
      if (d.field) {
        this.fieldErrors[d.field] = d.message;
      }
    }
  }

  get isSessionExpired(): boolean {
    return this.status === 401;
  }
}

export class ImportValidationError extends ApiError {
  constructor(message: string, errors: string[] = [], fieldErrors: Record<string, string> = {}) {
    const details: ErrorDetail[] = errors.map((e) => {
      const parts = e.split(":", 1);
      return parts.length > 1
        ? { field: parts[0].trim(), message: e.slice(parts[0].length + 1).trim() }
        : { message: e };
    });
    super(422, message, "VALIDATION_ERROR", details);
    this.name = "ImportValidationError";
    this.fieldErrors = fieldErrors;
  }
}

async function toError(res: Response): Promise<ApiError> {
  let body: any = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON body */
  }

  // 1. Direct match with standard backend envelope: { success: false, error: { code, message, status, details } }
  if (body?.error && typeof body.error === "object") {
    const code = body.error.code || (res.status === 422 ? "VALIDATION_ERROR" : "ERROR");
    const message = body.error.message || res.statusText || "Request failed";
    const rawDetails = Array.isArray(body.error.details) ? body.error.details : [];
    const details: ErrorDetail[] = rawDetails.map((d: any) => ({
      field: d.field || undefined,
      message: d.message || String(d),
    }));
    return new ApiError(res.status, message, code, details, body);
  }

  // 2. Fallbacks for legacy/unstandardized payloads
  const details: ErrorDetail[] = [];
  let mainMsg = "";

  if (Array.isArray(body?.errors)) {
    for (const item of body.errors) {
      if (typeof item === "string") {
        details.push({ message: item });
      } else if (item && typeof item === "object") {
        details.push({ field: item.field || undefined, message: item.msg || item.message || JSON.stringify(item) });
      }
    }
  }

  if (Array.isArray(body?.detail?.errors)) {
    for (const item of body.detail.errors) {
      const parts = String(item).split(":", 1);
      details.push(parts.length > 1 ? { field: parts[0].trim(), message: String(item).slice(parts[0].length + 1).trim() } : { message: String(item) });
    }
    if (typeof body.detail.message === "string") {
      mainMsg = body.detail.message;
    }
  } else if (Array.isArray(body?.detail)) {
    for (const d of body.detail) {
      const loc = Array.isArray(d.loc) ? d.loc.filter((x: any) => x !== "body").join(".") : "";
      details.push({ field: loc || undefined, message: d.msg || "Invalid value" });
    }
  } else if (typeof body?.detail === "string") {
    mainMsg = body.detail;
  } else if (typeof body?.message === "string") {
    mainMsg = body.message;
  }

  const code = res.status === 422 ? "VALIDATION_ERROR" : res.status === 401 ? "UNAUTHORIZED" : "ERROR";
  const formattedSummary = details.map((d) => (d.field ? `${d.field}: ${d.message}` : d.message)).join("; ");
  const finalMsg = mainMsg
    ? (formattedSummary && !mainMsg.includes(formattedSummary) ? `${mainMsg} (${formattedSummary})` : mainMsg)
    : (formattedSummary || res.statusText || "Request failed");

  return new ApiError(res.status, finalMsg, code, details, body);
}

let isRedirecting = false;

export function handleSessionExpired(customMsg?: string) {
  if (isRedirecting) return;
  isRedirecting = true;
  setStoredToken(null);

  if (typeof window !== "undefined") {
    import("sonner")
      .then(({ toast }) => {
        toast.error(customMsg || "Your session has expired. Please sign in again.");
      })
      .catch(() => {});

    // Redirect to landing page
    setTimeout(() => {
      window.location.href = "/";
      setTimeout(() => {
        isRedirecting = false;
      }, 3000);
    }, 400);
  }
}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  const token = await tokenProvider();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const base = getBaseUrl();
  let res: Response;
  try {
    res = await fetch(`${base}${path}`, {
      ...init,
      headers,
      credentials: "include", // send cookies for refresh token
    });
  } catch {
    throw new ApiError(0, "Can't reach the server. Check your connection and try again.");
  }

  // Handle 401 Unauthorized (Expired or invalid token)
  if (
    res.status === 401 &&
    !path.startsWith("/api/v1/auth/login") &&
    !path.startsWith("/api/v1/auth/register")
  ) {
    // Try to refresh token once if this is not already a refresh attempt
    if (path !== "/api/v1/auth/refresh") {
      try {
        const refreshRes = await fetch(`${base}/api/v1/auth/refresh`, {
          method: "POST",
          credentials: "include",
        });
        if (refreshRes.ok) {
          const refreshData = await refreshRes.json();
          if (refreshData?.access_token) {
            setStoredToken(refreshData.access_token);
            headers.set("Authorization", `Bearer ${refreshData.access_token}`);
            const retryRes = await fetch(`${base}${path}`, {
              ...init,
              headers,
              credentials: "include",
            });
            if (retryRes.ok) return retryRes;
          }
        }
      } catch {
        /* token refresh failed */
      }
    }

    // Refresh failed or invalid session: redirect to landing page with message
    handleSessionExpired("Your session has expired. Please sign in again.");
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
      json<ApiKey>("/api/v1/keys", {
        method: "POST",
        body: JSON.stringify({
          ...k,
          raw_key: k.api_key,
        }),
      }),
    remove: (id: string) => request(`/api/v1/keys/${id}`, { method: "DELETE" }),
    toggle: (id: string) => json<ApiKey>(`/api/v1/keys/${id}/toggle`, { method: "PATCH" }),
    models: () => json<ModelsResponse>("/api/v1/keys/models"),
  },
  resume: {
    generate: (b: GenerateRequest) =>
      json<ResumeResult>("/api/v1/resume/generate", { method: "POST", body: JSON.stringify(b) }),
    history: async (): Promise<HistoryItem[]> => {
      const res = await json<HistoryListResponse | HistoryItem[]>("/api/v1/history");
      if (Array.isArray(res)) return res;
      return res.items || [];
    },
    get: (id: string) => json<ResumeResult>(`/api/v1/resume/history/${id}`),
    downloadUrls: (id: string) =>
      json<DownloadUrlsResponse>(`/api/v1/history/${id}/download-urls`),
  },
};
