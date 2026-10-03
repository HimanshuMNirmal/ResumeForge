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
  public errors: string[];
  public fieldErrors: Record<string, string>;

  constructor(
    public status: number,
    message: string,
    public body?: unknown,
    errors: string[] = [],
    fieldErrors: Record<string, string> = {}
  ) {
    super(message);
    this.name = "ApiError";
    this.errors = errors;
    this.fieldErrors = fieldErrors;
  }
}

export class ImportValidationError extends ApiError {
  constructor(message: string, errors: string[], fieldErrors: Record<string, string> = {}) {
    super(422, message, undefined, errors, fieldErrors);
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

  const fieldErrors: Record<string, string> = {};
  const errorList: string[] = [];

  // 1. Extract from body.errors (array of strings or objects)
  if (Array.isArray(body?.errors)) {
    for (const item of body.errors) {
      if (typeof item === "string") {
        errorList.push(item);
      } else if (item && typeof item === "object") {
        const msg = item.msg || item.message || JSON.stringify(item);
        const loc = Array.isArray(item.loc) ? item.loc.filter((x: any) => x !== "body").join(".") : "";
        errorList.push(loc ? `${loc}: ${msg}` : msg);
        if (loc) fieldErrors[loc] = msg;
      }
    }
  }

  // 2. Extract from body.detail.errors (e.g. custom validator with { message, errors: [...] })
  if (Array.isArray(body?.detail?.errors)) {
    for (const item of body.detail.errors) {
      errorList.push(String(item));
      const parts = String(item).split(":");
      if (parts.length > 1) {
        fieldErrors[parts[0].trim()] = parts.slice(1).join(":").trim();
      }
    }
  }

  // 3. Extract from FastAPI default 422 validation array (body.detail: [{loc: [...], msg: "..."}])
  if (Array.isArray(body?.detail)) {
    for (const d of body.detail) {
      const locParts = Array.isArray(d.loc)
        ? d.loc.filter((x: any) => x !== "body")
        : [];
      const field = locParts.join(".");
      const msg = d.msg || "Invalid value";
      const formatted = field ? `${field}: ${msg}` : msg;
      errorList.push(formatted);
      if (field) fieldErrors[field] = msg;
    }
  }

  // 4. Extract base message
  let mainMsg = "";
  if (typeof body?.detail === "string") {
    mainMsg = body.detail;
  } else if (typeof body?.detail?.message === "string") {
    mainMsg = body.detail.message;
  } else if (typeof body?.message === "string") {
    mainMsg = body.message;
  }

  // Build the unified human-readable message
  let finalMessage = "";
  if (mainMsg && errorList.length > 0) {
    // If mainMsg already contains the error, don't duplicate
    if (errorList.some((e) => mainMsg.includes(e))) {
      finalMessage = mainMsg;
    } else {
      finalMessage = `${mainMsg} (${errorList.join("; ")})`;
    }
  } else if (errorList.length > 0) {
    finalMessage = errorList.join("; ");
  } else if (mainMsg) {
    finalMessage = mainMsg;
  } else {
    finalMessage = res.statusText || "Request failed";
  }

  if (res.status === 422 || errorList.length > 0) {
    return new ImportValidationError(finalMessage, errorList, fieldErrors);
  }
  return new ApiError(res.status, finalMessage, body, errorList, fieldErrors);
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
    history: () => json<ResumeResult[]>("/api/v1/resume/history"),
    get: (id: string) => json<ResumeResult>(`/api/v1/resume/history/${id}`),
  },
};
