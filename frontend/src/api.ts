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
  source_url: string;
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
const DEFAULT_TIMEOUT_MS = 90_000;

async function request<T>(path: string, init?: RequestInit, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  const abort = () => controller.abort();
  init?.signal?.addEventListener("abort", abort, { once: true });

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail ?? `Request failed (${response.status})`);
    }
    return payload as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Yêu cầu quá thời gian phản hồi. Vui lòng thử lại.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
    init?.signal?.removeEventListener("abort", abort);
  }
}

export const api = {
  health: () => request<Health>("/api/health", undefined, 15_000),
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
