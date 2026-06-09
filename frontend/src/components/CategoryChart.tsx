import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import type { CategorySummary } from "../types";
import { EXCLUDED_CATEGORIES } from "../types";
import { formatMoney } from "../lib/format";

export function CategoryChart({ data }: { data: CategorySummary[] }) {
  const spending = data
    .filter((d) => d.total > 0 && !EXCLUDED_CATEGORIES.has(d.category))
    .sort((a, b) => b.total - a.total);
  const excluded = data
    .filter((d) => d.total > 0 && EXCLUDED_CATEGORIES.has(d.category))
    .sort((a, b) => b.total - a.total);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <h2 className="mb-3 text-sm font-semibold text-slate-700">Spending by category</h2>
      {spending.length === 0 ? (
        <p className="text-sm text-slate-400">No spending categories.</p>
      ) : (
        <ResponsiveContainer width="100%" height={Math.max(160, spending.length * 36)}>
          <BarChart data={spending} layout="vertical" margin={{ left: 12, right: 16 }}>
            <XAxis type="number" tickFormatter={(v) => formatMoney(v)} fontSize={11} />
            <YAxis type="category" dataKey="category" width={128} fontSize={12} />
            <Tooltip formatter={(v: number) => formatMoney(v)} cursor={{ fill: "#f1f5f9" }} />
            <Bar dataKey="total" fill="#2563eb" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}

      {excluded.length > 0 && (
        <div className="mt-4 border-t border-slate-100 pt-3">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">
            Not counted as spend
          </p>
          <ul className="space-y-1 text-sm">
            {excluded.map((d) => (
              <li key={d.category} className="flex justify-between text-slate-500">
                <span>{d.category}</span>
                <span>{formatMoney(d.total)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}