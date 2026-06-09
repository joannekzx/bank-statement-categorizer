import { useState } from "react";
import { analyzeStatement, correctCategory } from "./api";
import type { AnalysisResult } from "./types";
import { recompute } from "./lib/aggregate";
import { UploadZone } from "./components/UploadZone";
import { Dashboard } from "./components/Dashboard";

export default function App() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);

  async function handleFile(file: File) {
    setLoading(true);
    setError(null);
    try {
      setResult(await analyzeStatement(file));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function handleCorrect(merchant: string, category: string) {
    if (!result) return;
    setSaving(merchant);

    // Optimistic local update: every row of this merchant, then re-aggregate.
    const updatedTx = result.transactions.map((tx) =>
      tx.merchant === merchant ? { ...tx, category } : tx,
    );
    const agg = recompute(updatedTx);
    setResult({ ...result, transactions: updatedTx, ...agg });

    try {
      await correctCategory(merchant, category); // persists to the cache
    } catch {
      setError(`Saved locally, but couldn't persist "${merchant}" to the server.`);
    } finally {
      setSaving(null);
    }
  }

  function reset() {
    setResult(null);
    setError(null);
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {result ? (
        <Dashboard result={result} onReset={reset} onCorrect={handleCorrect} saving={saving} />
      ) : (
        <div className="mx-auto flex min-h-screen max-w-xl flex-col justify-center px-4">
          <h1 className="mb-2 text-3xl font-bold text-slate-900">Statement Categorizer</h1>
          <p className="mb-6 text-slate-500">
            Upload a UOB savings statement (PDF) to see categorized spending.
          </p>
          <UploadZone onFile={handleFile} loading={loading} error={error} />
        </div>
      )}
    </div>
  );
}