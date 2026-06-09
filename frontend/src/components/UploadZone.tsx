import { useRef, useState } from "react";

interface Props {
  onFile: (file: File) => void;
  loading: boolean;
  error: string | null;
}

export function UploadZone({ onFile, loading, error }: Props) {
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function pick(files: FileList | null) {
    if (!files || files.length === 0) return;
    const file = files[0];
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setLocalError("Please choose a PDF file.");
    } else {
      setLocalError(null);
      onFile(file);
    }
    if (inputRef.current) inputRef.current.value = ""; // allow re-picking same file
  }

  const message = localError ?? error;

  return (
    <div>
      <div
        onClick={() => !loading && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); if (!loading) setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (!loading) pick(e.dataTransfer.files);
        }}
        className={[
          "flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-12 text-center transition-colors",
          dragging ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-white hover:border-slate-400",
          loading ? "pointer-events-none opacity-70" : "",
        ].join(" ")}
      >
        {loading ? (
          <>
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-300 border-t-blue-600" />
            <p className="mt-4 font-medium text-slate-700">Analyzing your statement…</p>
            <p className="mt-1 text-sm text-slate-400">
              A fresh statement can take 5–10 seconds while new merchants are categorized.
            </p>
          </>
        ) : (
          <>
            <p className="text-lg font-medium text-slate-700">Drop a PDF here</p>
            <p className="mt-1 text-sm text-slate-400">or click to browse</p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          className="hidden"
          onChange={(e) => pick(e.target.files)}
        />
      </div>

      {message && !loading && (
        <p className="mt-3 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">{message}</p>
      )}
    </div>
  );
}