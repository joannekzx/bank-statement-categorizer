import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  ResponsiveContainer,
} from "recharts";
import type { Trends } from "../types";
import { getTrends } from "../api";
import { formatMoney } from "../lib/format";

// A fixed palette so each category keeps a stable colour across renders.
const LINE_COLORS = [
  "#2563eb", "#f97316", "#16a34a", "#db2777",
  "#9333ea", "#0891b2", "#ca8a04", "#dc2626",
];
const MAX_SERIES = 6; // keep the chart legible; chart the biggest spenders

export function TrendsView() {
  const [trends, setTrends] = useState<Trends | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    getTrends()
      .then(setTrends)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!trends) return <p className="text-sm text-slate-400">Loading…</p>;

  // Every month that appears anywhere, sorted (months are "YYYY-MM" strings).
  const months = [
    ...new Set(Object.values(trends).flatMap((m) => Object.keys(m))),
  ].sort();

  if (months.length < 2) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center">
        <p className="text-sm font-medium text-slate-600">Not enough data yet</p>
        <p className="mt-1 text-sm text-slate-400">
          Trends need at least 2 months of statements. Upload another month and
          this fills in.
        </p>
      </div>
    );
  }

  // Rank categories by total spend; chart the top MAX_SERIES.
  const ranked = Object.entries(trends)
    .map(([cat, byMonth]) => ({
      cat,
      total: Object.values(byMonth).reduce((a, b) => a + b, 0),
    }))
    .sort((a, b) => b.total - a.total)
    .slice(0, MAX_SERIES)
    .map((r) => r.cat);

  // Recharts wants one row per month with a key per category.
  const data = months.map((month) => {
    const row: Record<string, string | number> = { month };
    for (const cat of ranked) row[cat] = trends[cat]?.[month] ?? 0;
    return row;
  });

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <h2 className="mb-4 text-sm font-semibold text-slate-700">
        Spending by category over time
      </h2>
      <ResponsiveContainer width="100%" height={360}>
        <LineChart data={data} margin={{ left: 8, right: 16, top: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="month" fontSize={12} />
          <YAxis tickFormatter={(v) => formatMoney(Number(v))} fontSize={11} width={72} />
          <Tooltip formatter={(v) => formatMoney(Number(v))} />
          <Legend />
          {ranked.map((cat, i) => (
            <Line
              key={cat}
              type="monotone"
              dataKey={cat}
              stroke={LINE_COLORS[i % LINE_COLORS.length]}
              strokeWidth={2}
              dot={{ r: 3 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
