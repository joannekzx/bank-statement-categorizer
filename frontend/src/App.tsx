import { useState, type ReactNode } from "react";
import { analyzeStatement, correctCategory, getStatement } from "./api";
import type { AnalysisResult } from "./types";
import { recompute } from "./lib/aggregate";
import { UploadZone } from "./components/UploadZone";
import { Dashboard } from "./components/Dashboard";
import { StatementHistory } from "./components/StatementHistory";
import { TrendsView } from "./components/TrendsView";
import { ReimbursementReview } from "./components/ReimbursementReview";

type View = "upload" | "history" | "trends";

const TABS: { key: View; label: string }[] = [
  { key: "upload", label: "Upload" },
  { key: "history", label: "History" },
  { key: "trends", label: "Trends" },
];

export default function App() {
  const [view, setView] = useState<View>("upload");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const [historyKey, setHistoryKey] = useState(0); // bump to refetch history

  async function handleFile(file: File) {
    setLoading(true);
    setError(null);
    try {
      setResult(await analyzeStatement(file));
      setHistoryKey((k) => k + 1); // a new statement now exists in history
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function openStatement(id: number) {
    setError(null);
    try {
      setResult(await getStatement(id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't open statement");
    }
  }

  async function reloadCurrent() {
    if (result?.id == null) return;
    try {
      setResult(await getStatement(result.id));
    } catch {
      /* keep the stale view; the offset still saved server-side */
    }
  }

  async function handleCorrect(merchant: string, category: string) {
    if (!result) return;
    setSaving(merchant);
    const updatedTx = result.transactions.map((tx) =>
      tx.merchant === merchant ? { ...tx, category } : tx,
    );
    const agg = recompute(updatedTx);
    setResult({ ...result, transactions: updatedTx, ...agg });
    try {
      await correctCategory(merchant, category);
    } catch {
      setError(`Saved locally, but couldn't persist "${merchant}" to the server.`);
    } finally {
      setSaving(null);
    }
  }

  function backToList() {
    setResult(null);
    setReviewing(false);
    setError(null);
  }

  // A statement is open: show its dashboard (or the reimbursement review).
  if (result) {
    if (reviewing && result.id != null) {
      return (
        <Shell view={view} onNav={(v) => { backToList(); setView(v); }}>
          <ReimbursementReview
            statementId={result.id}
            onConfirmed={reloadCurrent}
            onBack={() => setReviewing(false)}
          />
        </Shell>
      );
    }
    return (
      <Dashboard
        result={result}
        onReset={backToList}
        onCorrect={handleCorrect}
        saving={saving}
        onReviewReimbursements={result.id != null ? () => setReviewing(true) : undefined}
      />
    );
  }

  return (
    <Shell view={view} onNav={setView}>
      {error && (
        <p className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700">{error}</p>
      )}
      {view === "upload" && (
        <div className="mx-auto max-w-xl">
          <p className="mb-6 text-slate-500">
            Upload a UOB savings statement (PDF) to see categorized spending. Your
            statements are saved so you can revisit them and see trends.
          </p>
          <UploadZone onFile={handleFile} loading={loading} error={null} />
        </div>
      )}
      {view === "history" && <StatementHistory onOpen={openStatement} refreshKey={historyKey} />}
      {view === "trends" && <TrendsView />}
    </Shell>
  );
}

function Shell({
  view,
  onNav,
  children,
}: {
  view: View;
  onNav: (v: View) => void;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <h1 className="flex items-center gap-2 text-[15px] font-semibold tracking-tight text-slate-900">
            <span className="h-4 w-1 rounded-sm bg-green-700" aria-hidden />
            Statement Categorizer
          </h1>
          <nav className="flex gap-0.5">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => onNav(t.key)}
                className={[
                  "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                  view === t.key
                    ? "bg-slate-100 text-slate-900"
                    : "text-slate-500 hover:text-slate-900",
                ].join(" ")}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
    </div>
  );
}
