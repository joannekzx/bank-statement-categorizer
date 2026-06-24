import { useEffect, useState } from "react";
import type { ReimbursementSuggestion, Transaction } from "../types";
import { getReimbursements, confirmOffset } from "../api";
import { formatMoney, formatDate } from "../lib/format";

interface Props {
  statementId: number;
  onConfirmed: () => void; // reload the dashboard so totals reflect the offset
  onBack: () => void;
}

export function ReimbursementReview({ statementId, onConfirmed, onBack }: Props) {
  const [suggestions, setSuggestions] = useState<ReimbursementSuggestion[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  // transfer tx id -> chosen spend tx id
  const [picked, setPicked] = useState<Record<number, number>>({});
  const [busy, setBusy] = useState<number | null>(null);
  const [done, setDone] = useState<Set<number>>(new Set());

  function load() {
    getReimbursements(statementId)
      .then(setSuggestions)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }

  useEffect(load, [statementId]);

  async function confirm(transfer: Transaction, spend: Transaction) {
    if (transfer.id == null || spend.id == null) return;
    setBusy(transfer.id);
    setError(null);
    const amount = Math.min(transfer.amount, -spend.amount);
    try {
      await confirmOffset(transfer.id, spend.id, amount);
      setDone((d) => new Set(d).add(transfer.id!));
      onConfirmed(); // refresh dashboard totals behind this view
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't save");
    } finally {
      setBusy(null);
    }
  }

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!suggestions) return <p className="text-sm text-slate-400">Loading…</p>;

  const open = suggestions.filter((s) => s.transfer.id != null && !done.has(s.transfer.id));

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Reimbursement review</h2>
          <p className="text-sm text-slate-500">
            Inbound transfers that may pay you back for a recent spend. Confirm a
            match to subtract it from that category — nothing is applied
            automatically.
          </p>
        </div>
        <button
          onClick={onBack}
          className="shrink-0 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Back
        </button>
      </div>

      {open.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-400">
          {suggestions.length === 0
            ? "No likely reimbursements found in this statement."
            : "All suggestions reviewed."}
        </p>
      ) : (
        <ul className="space-y-4">
          {open.map((s) => {
            const transfer = s.transfer;
            const chosen = picked[transfer.id!];
            return (
              <li
                key={transfer.id}
                className="rounded-2xl border border-slate-200 bg-white p-5"
              >
                <p className="text-sm text-slate-500">Inbound transfer</p>
                <p className="mb-3 font-medium text-green-700">
                  +{formatMoney(transfer.amount)} from {transfer.merchant} ·{" "}
                  {formatDate(transfer.date)}
                </p>
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">
                  Does it offset one of these spends?
                </p>
                <div className="space-y-1.5">
                  {s.candidates.map((c) => (
                    <label
                      key={c.id}
                      className={[
                        "flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2 text-sm",
                        chosen === c.id
                          ? "border-blue-400 bg-blue-50"
                          : "border-slate-200 hover:bg-slate-50",
                      ].join(" ")}
                    >
                      <input
                        type="radio"
                        name={`transfer-${transfer.id}`}
                        checked={chosen === c.id}
                        onChange={() =>
                          setPicked((p) => ({ ...p, [transfer.id!]: c.id! }))
                        }
                      />
                      <span className="flex-1 text-slate-700">
                        −{formatMoney(c.amount)} · {c.merchant}
                        <span className="text-slate-400"> ({c.category})</span>
                      </span>
                      <span className="text-slate-400">{formatDate(c.date)}</span>
                    </label>
                  ))}
                </div>
                <div className="mt-3 flex gap-2">
                  <button
                    disabled={chosen == null || busy === transfer.id}
                    onClick={() =>
                      confirm(transfer, s.candidates.find((c) => c.id === chosen)!)
                    }
                    className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
                  >
                    {busy === transfer.id ? "Saving…" : "Confirm offset"}
                  </button>
                  <button
                    onClick={() =>
                      setDone((d) => new Set(d).add(transfer.id!))
                    }
                    className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
                  >
                    Dismiss
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
