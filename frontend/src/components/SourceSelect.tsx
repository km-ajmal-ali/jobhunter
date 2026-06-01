import { useState, useRef, useEffect } from "react";
import type { SourceInfo } from "../types";

interface SourceSelectProps {
  sources: SourceInfo[];
  value: string;
  onChange: (name: string) => void;
}

export default function SourceSelect({ sources, value, onChange }: SourceSelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const selected = sources.find((s) => s.name === value);

  return (
    <div ref={ref} className="relative w-44">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="input-field flex w-full items-center gap-2 text-left"
      >
        {selected ? (
          <>
            <span className="truncate flex-1">{selected.name.charAt(0).toUpperCase() + selected.name.slice(1)}</span>
            <span className="text-gray-400 text-xs">{selected.total_jobs}</span>
          </>
        ) : (
          <span className="text-gray-500">All Sources</span>
        )}
        <svg className={`ml-auto h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {open && (
        <ul className="absolute z-50 mt-1 max-h-60 w-full overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg">
          <li>
            <button
              type="button"
              onClick={() => { onChange(""); setOpen(false); }}
              className={`flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-gray-100 ${!value ? "bg-primary-50 font-medium" : ""}`}
            >
              All Sources
            </button>
          </li>
          {sources.map((s) => (
            <li key={s.name}>
              <button
                type="button"
                onClick={() => { onChange(s.name); setOpen(false); }}
                className={`flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-gray-100 ${s.name === value ? "bg-primary-50 font-medium" : ""}`}
              >
                <span className="truncate flex-1">{s.name.charAt(0).toUpperCase() + s.name.slice(1)}</span>
                <span className="text-gray-400 text-xs">{s.total_jobs}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
