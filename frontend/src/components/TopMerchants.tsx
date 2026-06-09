
import type { MerchantSummary } from "../types";
import { formatMoney } from "../lib/format";

export function TopMerchants({ data }: { data: MerchantSummary[] }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <h2 className="mb-3 text-sm font-semibold text-slate-700">Top merchants</h2>
      {data.length === 0 ? (
        <p className="text-sm text-slate-400">No merchants.</p>
      ) : (
        <ol className="space-y-2">
          {data.map((m, i) => (
            <li key={m.merchant} className="flex items-center gap-3 text-sm">
              <span className="w-5 text-right text-slate-400">{i + 1}</span>
              <span className="flex-1 truncate text-slate-700" title={m.merchant}>{m.merchant}</span>
              <span className="text-slate-400">{m.count}×</span>
              <span className="w-20 text-right font-medium text-slate-900">{formatMoney(m.total)}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}