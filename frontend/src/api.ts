import type {
  AnalysisResult,
  ReimbursementSuggestion,
  StatementSummary,
  Trends,
} from "./types";

const BASE = "http://localhost:8000";

const NETWORK_MSG =
  "Couldn't reach the server. Is the backend running on port 8000?";

async function getJson<T>(path: string): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(`${BASE}${path}`);
  } catch {
    throw new Error(NETWORK_MSG);
  }
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail ?? `Request failed (${resp.status})`);
  }
  return resp.json();
}

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

export function listStatements(): Promise<StatementSummary[]> {
  return getJson("/statements");
}

export function getStatement(id: number): Promise<AnalysisResult> {
  return getJson(`/statements/${id}`);
}

export function getTrends(): Promise<Trends> {
  return getJson("/trends");
}

export function getReimbursements(
  statementId: number,
): Promise<ReimbursementSuggestion[]> {
  return getJson(`/statements/${statementId}/reimbursements`);
}

export async function confirmOffset(
  transferTxId: number,
  spendTxId: number,
  amount: number,
): Promise<void> {
  let resp: Response;
  try {
    resp = await fetch(`${BASE}/offsets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        transfer_tx_id: transferTxId,
        spend_tx_id: spendTxId,
        amount,
      }),
    });
  } catch {
    throw new Error(NETWORK_MSG);
  }
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail ?? `Couldn't save offset (${resp.status})`);
  }
}