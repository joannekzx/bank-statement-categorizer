import type { AnalysisResult } from "../types";
import { formatMoney, formatPeriod } from "../lib/format";
import { transactionsToCsv, downloadCsv, csvFilename } from "../lib/csv";
import { CategoryChart } from "./CategoryChart";
import { TopMerchants } from "./TopMerchants";
import { TransactionTable } from "./TransactionTable";

interface Props {
  result: AnalysisResult;
  onReset: () => void;
  onCorrect: (merchant: string, category: string) => void;
  saving: string | null;
  // Available only for persisted statements (those with an id).
  onReviewReimbursements?: () => void;
}

export function Dashboard({ result, onReset, onCorrect, saving, onReviewReimbursements }: Props) {
  function handleDownload() {
    const csv = transactionsToCsv(result.transactions);
    downloadCsv(csvFilename(result.bank, result.period_start), csv);
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-900">{result.bank} statement</h1>
          <p className="text-sm text-slate-500">{formatPeriod(result.period_start, result.period_end)}</p>
        </div>
        <div className="flex gap-2">
          {onReviewReimbursements && (
            <button
              onClick={onReviewReimbursements}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Review reimbursements
            </button>
          )}
          <button
            onClick={handleDownload}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Download CSV
          </button>
          <button
            onClick={onReset}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Analyze another
          </button>
        </div>
      </div>

      <div className="mt-6 flex items-end justify-between border-y border-slate-200 py-5">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Total spend</p>
          <p className="tnum mt-1.5 text-4xl font-semibold tracking-tight text-green-800">
            {formatMoney(result.total_spend)}
          </p>
        </div>
        <p className="tnum text-sm text-slate-500">
          {result.transactions.length} transactions · {result.by_category.length} categories
        </p>
      </div>

      <div className="mt-6 grid gap-5 md:grid-cols-2">
        <CategoryChart data={result.by_category} />
        <TopMerchants data={result.top_merchants} />
      </div>
      <div className="mt-5">
        <TransactionTable transactions={result.transactions} onCorrect={onCorrect} saving={saving} />
      </div>
    </div>
  );
}