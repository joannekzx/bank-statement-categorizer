const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// Unsigned "$1,234.56". Components decide sign/colour for spend vs refund.
export function formatMoney(n: number): string {
  return "$" + Math.abs(n).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

// "1 Apr 2026" — parse the ISO parts manually to dodge timezone off-by-one.
export function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]} ${y}`;
}

// "1 Apr – 30 Apr 2026" (drops the year on the start date when it matches).
export function formatPeriod(startIso: string, endIso: string): string {
  const [sy, sm, sd] = startIso.split("-").map(Number);
  const [ey, em, ed] = endIso.split("-").map(Number);
  const start = sy === ey ? `${sd} ${MONTHS[sm - 1]}` : `${sd} ${MONTHS[sm - 1]} ${sy}`;
  return `${start} – ${ed} ${MONTHS[em - 1]} ${ey}`;
}