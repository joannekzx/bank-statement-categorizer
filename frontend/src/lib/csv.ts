import type { Transaction } from "../types";

export function transactionsToCsv(txs: Transaction[]): string {
  const header = ["date", "merchant", "description", "amount", "category"];
  const rows = txs.map((t) =>
    [
      t.date,
      t.merchant,
      t.description.replace(/"/g, '""'), // escape embedded quotes
      t.amount.toFixed(2),
      t.category ?? "",
    ]
      .map((field) => `"${field}"`)
      .join(","),
  );
  return [header.join(","), ...rows].join("\n");
}

export function downloadCsv(filename: string, csv: string) {
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// "uob_2026-04.csv" from the period start.
export function csvFilename(bank: string, periodStart: string): string {
  const [y, m] = periodStart.split("-");
  return `${bank.toLowerCase()}_${y}-${m}.csv`;
}