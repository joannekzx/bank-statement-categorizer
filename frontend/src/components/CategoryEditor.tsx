import { useEffect, useRef } from "react";
import { CATEGORIES } from "../types";
import { categoryClasses } from "../lib/categories";

interface Props {
  current: string | null;
  onPick: (category: string) => void;
  onClose: () => void;
}

export function CategoryEditor({ current, onPick, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
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
  }, [onClose]);

  return (
    <div
      ref={ref}
      className="absolute z-20 mt-1 w-56 rounded-xl border border-slate-200 bg-white p-1.5 shadow-lg"
    >
      <p className="px-2 py-1 text-xs text-slate-400">Change category</p>
      <div className="grid grid-cols-2 gap-1">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => onPick(cat)}
            className={[
              "rounded-lg px-2 py-1 text-left text-xs font-medium hover:ring-2 hover:ring-blue-300",
              categoryClasses(cat),
              cat === current ? "ring-2 ring-blue-400" : "",
            ].join(" ")}
          >
            {cat}
          </button>
        ))}
      </div>
    </div>
  );
}