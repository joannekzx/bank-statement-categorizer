// Muted, harmonious tints (soft -50 backgrounds, -700 ink) — enough hue to tell
// categories apart at a glance without the neon-highlighter look.
export const CATEGORY_COLORS: Record<string, string> = {
  Food: "bg-orange-50 text-orange-700",
  Groceries: "bg-lime-50 text-lime-700",
  Transport: "bg-sky-50 text-sky-700",
  Shopping: "bg-rose-50 text-rose-700",
  Subscriptions: "bg-indigo-50 text-indigo-700",
  "Bills & Utilities": "bg-amber-50 text-amber-700",
  Health: "bg-teal-50 text-teal-700",
  Entertainment: "bg-violet-50 text-violet-700",
  Travel: "bg-cyan-50 text-cyan-700",
  Investments: "bg-emerald-50 text-emerald-700",
  Transfers: "bg-slate-100 text-slate-600",
  Income: "bg-green-50 text-green-700",
  Other: "bg-slate-100 text-slate-500",
};

export function categoryClasses(category: string | null): string {
  return (category && CATEGORY_COLORS[category]) || "bg-slate-100 text-slate-500";
}
