import { useEffect, useState } from "react";
import type { StatementSummary } from "../types";
import { listStatements } from "../api";
import { formatMoney, formatPeriod, formatDate } from "../lib/format";

interface Props {
  onOpen: (id: number) => void;
  // Bumped by the parent after an upload so the list refetches.
  refreshKey?: number;
}

export function StatementHistory({ onOpen, refreshKey }: Props) {
  const [statements, setStatements] = useState<StatementSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    listStatements()
      .then(setStatements)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, [refreshKey]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!statements) return <p className="text-sm text-slate-400">Loading…</p>;

  if (statements.length === 0) {
    return (
      <p className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-400">
        No statements yet. Upload one to get started.
      </p>
    );
  }

  return (
    <ul className="space-y-2">
      {statements.map((s) => (
        <li key={s.id}>
          <button
            onClick={() => onOpen(s.id)}
            className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-white px-5 py-4 text-left hover:border-blue-300 hover:bg-slate-50"
          >
            <div>
              <p className="font-medium text-slate-800">
                {s.bank} · {formatPeriod(s.period_start, s.period_end)}
              </p>
              <p className="text-xs text-slate-400">
                {s.transaction_count} transactions · uploaded {formatDate(s.uploaded_at.slice(0, 10))}
              </p>
            </div>
            <span className="text-lg font-semibold text-slate-900">
              {formatMoney(s.total_spend)}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
