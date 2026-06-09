import type { AnalysisResult } from "./types";

const BASE = "http://localhost:8000";

const NETWORK_MSG =
  "Couldn't reach the server. Is the backend running on port 8000?";

export async function analyzeStatement(file: File): Promise<AnalysisResult> {
  const form = new FormData();
  form.append("file", file);

  let resp: Response;
  try {
    resp = await fetch(`${BASE}/analyze`, { method: "POST", body: form });
  } catch {
    throw new Error(NETWORK_MSG); // fetch rejects on connection failure / CORS
  }

  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail ?? `Request failed (${resp.status})`);
  }
  return resp.json();
}

export async function correctCategory(merchant: string, category: string): Promise<void> {
  let resp: Response;
  try {
    resp = await fetch(`${BASE}/correct`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ merchant, category }),
    });
  } catch {
    throw new Error(NETWORK_MSG);
  }
  if (!resp.ok) throw new Error(`Correction failed (${resp.status})`);
}