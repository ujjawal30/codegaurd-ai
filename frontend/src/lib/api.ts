/**
 * CodeGuard AI — API Client
 *
 * Axios-based HTTP client + SSE helper for real-time progress streaming.
 */

import axios from "axios";

// Runtime env (production) → build-time env (development) → fallback
const API_BASE = (window as unknown as Record<string, Record<string, string>>).__ENV__?.VITE_API_URL ?? import.meta.env.VITE_API_URL ?? "/api";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 60_000,
  headers: { "Content-Type": "application/json" },
});

/* ── Upload ──────────────────────────────────────────────────── */

export async function uploadZip(file: File) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/upload/", form, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120_000,
  });
  return data as {
    job_id: string;
    filename: string;
    status: string;
    message: string;
  };
}

/* ── Analyze ─────────────────────────────────────────────────── */

export async function triggerAnalysis(jobId: string) {
  const { data } = await api.post(`/analyze/${jobId}`);
  return data;
}

export async function getAnalysis(jobId: string) {
  const { data } = await api.get(`/analyze/${jobId}`);
  return data;
}

export async function getAnalysisStatus(jobId: string) {
  const { data } = await api.get(`/analyze/${jobId}/status`);
  return data as {
    job_id: string;
    status: string;
    current_stage: string | null;
    progress_pct: number;
    error_message: string | null;
  };
}

/* ── Analyses List ───────────────────────────────────────────── */

export async function listAnalyses(page = 1, pageSize = 10) {
  const { data } = await api.get("/analyses/", {
    params: { page, page_size: pageSize },
  });
  return data;
}

/* ── SSE Progress Stream ─────────────────────────────────────── */

export type ProgressEvent = {
  job_id: string;
  status: string;
  stage: string;
  progress: number;
  error?: string;
};

export function subscribeProgress(
  jobId: string,
  onProgress: (ev: ProgressEvent) => void,
  onComplete: (ev: ProgressEvent) => void,
  onError: (ev: ProgressEvent | string) => void,
): () => void {
  const url = `${API_BASE}/progress/${jobId}`;
  const es = new EventSource(url);

  es.addEventListener("progress", (e) => {
    onProgress(JSON.parse(e.data));
  });

  es.addEventListener("complete", (e) => {
    onComplete(JSON.parse(e.data));
    es.close();
  });

  es.addEventListener("error", (e) => {
    if (e instanceof MessageEvent) {
      onError(JSON.parse(e.data));
    } else {
      onError("Connection lost");
    }
    es.close();
  });

  // Return cleanup function
  return () => es.close();
}
