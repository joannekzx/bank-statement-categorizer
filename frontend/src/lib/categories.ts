export const CATEGORY_COLORS: Record<string, string> = {
  Food: "bg-orange-100 text-orange-700",
  Groceries: "bg-lime-100 text-lime-700",
  Transport: "bg-sky-100 text-sky-700",
  Shopping: "bg-pink-100 text-pink-700",
  Subscriptions: "bg-violet-100 text-violet-700",
  "Bills & Utilities": "bg-amber-100 text-amber-700",
  Health: "bg-rose-100 text-rose-700",
  Entertainment: "bg-fuchsia-100 text-fuchsia-700",
  Travel: "bg-cyan-100 text-cyan-700",
  Investments: "bg-emerald-100 text-emerald-700",
  Transfers: "bg-slate-100 text-slate-600",
  Income: "bg-green-100 text-green-700",
  Other: "bg-slate-200 text-slate-600",
};

export function categoryClasses(category: string | null): string {
  return (category && CATEGORY_COLORS[category]) || "bg-slate-200 text-slate-600";
}
