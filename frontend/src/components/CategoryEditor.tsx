import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { CATEGORIES } from "../types";
import { categoryClasses } from "../lib/categories";

interface Props {
  anchor: HTMLElement; // the pill that was clicked; the popup anchors to it
  current: string | null;
  onPick: (category: string) => void;
  onClose: () => void;
}

const WIDTH = 288; // px (matches w-72)
const GAP = 6;
const MARGIN = 8;

export function CategoryEditor({ anchor, current, onPick, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const [query, setQuery] = useState("");

  const q = query.trim().toLowerCase();
  const filtered = q
    ? CATEGORIES.filter((c) => c.toLowerCase().includes(q))
    : CATEGORIES;

  // Position as a fixed-layer popover anchored to the pill, flipping above /
  // clamping to the viewport so it's never clipped by a scroll container.
  const place = useCallback(() => {
    const r = anchor.getBoundingClientRect();
    const height = ref.current?.offsetHeight ?? 0;

    let left = Math.min(r.left, window.innerWidth - WIDTH - MARGIN);
    left = Math.max(MARGIN, left);

    let top = r.bottom + GAP;
    if (height && top + height > window.innerHeight - MARGIN) {
      top = Math.max(MARGIN, r.top - height - GAP); // not enough room below → flip up
    }
    setPos({ top, left });
  }, [anchor]);

  useLayoutEffect(() => {
    place();
    window.addEventListener("scroll", place, true); // capture: catch inner scrolls too
    window.addEventListener("resize", place);
    return () => {
      window.removeEventListener("scroll", place, true);
      window.removeEventListener("resize", place);
    };
  }, [place]);

  // Re-anchor when filtering changes the popup's height (e.g. it flipped up).
  useLayoutEffect(() => {
    place();
  }, [filtered.length, place]);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      const t = e.target as Node;
      // Clicks on the anchor itself are handled by the table's toggle.
      if (ref.current && !ref.current.contains(t) && !anchor.contains(t)) onClose();
    }
    function onEsc(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onEsc);
    };
  }, [onClose, anchor]);

  return createPortal(
    <div
      ref={ref}
      role="menu"
      style={{
        position: "fixed",
        top: pos?.top ?? -9999,
        left: pos?.left ?? -9999,
        width: WIDTH,
        visibility: pos ? "visible" : "hidden",
      }}
      className="z-50 rounded-2xl border border-slate-200 bg-white p-2 shadow-xl ring-1 ring-black/5"
    >
      <input
        autoFocus
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => {
          // Enter picks the top match — fast path for "type a few letters, hit enter".
          if (e.key === "Enter" && filtered.length > 0) {
            e.preventDefault();
            onPick(filtered[0]);
          }
        }}
        placeholder="Search category…"
        className="mb-2 w-full rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm text-slate-700 outline-none placeholder:text-slate-400 focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
      />
      {filtered.length === 0 ? (
        <p className="px-1.5 py-2 text-center text-xs text-slate-400">
          No categories match “{query}”.
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-1.5">
          {filtered.map((cat) => {
            const selected = cat === current;
            return (
              <button
                key={cat}
                role="menuitem"
                onClick={() => onPick(cat)}
                className={[
                  "truncate rounded-lg px-2.5 py-1.5 text-left text-xs font-medium transition",
                  categoryClasses(cat),
                  selected
                    ? "ring-2 ring-blue-500"
                    : "ring-1 ring-transparent hover:ring-2 hover:ring-blue-300",
                ].join(" ")}
                title={cat}
              >
                {cat}
              </button>
            );
          })}
        </div>
      )}
    </div>,
    document.body,
  );
}
