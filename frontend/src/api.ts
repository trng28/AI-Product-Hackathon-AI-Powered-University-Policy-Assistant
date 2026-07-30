export type Health = {
  status: "ready" | "index_required" | "configuration_required";
  provider?: string;
  model?: string;
  index_ready: boolean;
  detail?: string;
};

export type Citation = {
  chunk_id: string;
  article: string;
  clause: string;
  page: number;
  document: string;
  support: string;
};

export type Answer = {
  answer: string;
  citations: Citation[];
  confidence: number;
  evidence_sufficient: boolean;
  query_understanding: {
    intent?: string;
    topic?: string;
    keywords?: string[];
    rewritten_query?: string;
  };
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail ?? `Request failed (${response.status})`);
  }
  return payload as T;
}

export const api = {
  health: () => request<Health>("/api/health"),
  ask: (question: string) =>
    request<Answer>("/api/ask", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
  buildIndex: () =>
    request<{ chunks: number }>("/api/index", {
      method: "POST",
      body: JSON.stringify({ pdf_paths: [], force: false }),
    }),
};
