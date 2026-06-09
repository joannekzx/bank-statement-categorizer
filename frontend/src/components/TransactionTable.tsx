import { useState } from "react";
import type { Transaction } from "../types";
import { formatMoney, formatDate } from "../lib/format";
import { CategoryEditor } from "./CategoryEditor";
import { categoryClasses } from "../lib/categories";

interface Props {
  transactions: Transaction[];
  // Provided in Step 8: applies a correction to ALL rows of this merchant.
  onCorrect?: (merchant: string, category: string) => void;
  saving?: string | null; // merchant currently being saved, for a subtle hint
}

export function TransactionTable({ transactions, onCorrect, saving }: Props) {
  const [openRow, setOpenRow] = useState<number | null>(null);

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
        <h2 className="text-sm font-semibold text-slate-700">Transactions</h2>
        <span className="text-xs text-slate-400">{transactions.length} rows</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-400">
              <th className="px-5 py-2 font-medium">Date</th>
              <th className="px-5 py-2 font-medium">Merchant</th>
              <th className="px-5 py-2 text-right font-medium">Amount</th>
              <th className="px-5 py-2 font-medium">Category</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx, i) => {
              const isSpend = tx.amount < 0;
              return (
                <tr key={i} className="border-b border-slate-50 last:border-0 hover:bg-slate-50">
                  <td className="whitespace-nowrap px-5 py-2.5 text-slate-500">{formatDate(tx.date)}</td>
                  <td className="px-5 py-2.5 text-slate-800">
                    <span className="block max-w-xs truncate" title={tx.description}>{tx.merchant}</span>
                  </td>
                  <td className={`whitespace-nowrap px-5 py-2.5 text-right font-medium ${isSpend ? "text-red-600" : "text-green-600"}`}>
                    {isSpend ? "−" : "+"}{formatMoney(tx.amount)}
                  </td>
                  <td className="relative px-5 py-2.5">
                    <button
                      onClick={() => onCorrect && setOpenRow(openRow === i ? null : i)}
                      disabled={!onCorrect}
                      className={[
                        `inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${categoryClasses(tx.category)}`,
                        onCorrect ? "cursor-pointer hover:ring-2 hover:ring-blue-300" : "cursor-default",
                        saving === tx.merchant ? "opacity-50" : "",
                      ].join(" ")}
                      title={onCorrect ? "Click to change category" : undefined}
                    >
                      {tx.category ?? "—"}
                    </button>
                    {openRow === i && onCorrect && (
                      <CategoryEditor
                        current={tx.category}
                        onClose={() => setOpenRow(null)}
                        onPick={(cat) => {
                          setOpenRow(null);
                          onCorrect(tx.merchant, cat);
                        }}
                      />
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}