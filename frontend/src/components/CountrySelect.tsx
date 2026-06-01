import { useState, useRef, useEffect } from "react";
import * as flags from "country-flag-icons/react/3x2";
import type { CountryInfo } from "../types";

interface CountrySelectProps {
  countries: CountryInfo[];
  value: string;
  onChange: (code: string) => void;
}

export default function CountrySelect({ countries, value, onChange }: CountrySelectProps) {
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

  const selected = countries.find((c) => c.code === value);

  function FlagIcon({ code, className }: { code: string; className?: string }) {
    const Flag = (flags as Record<string, React.ComponentType<{ className?: string }>>)[code.toUpperCase()];
    return Flag ? <Flag className={className || "inline-block w-5 h-3.5 align-middle"} /> : null;
  }

  return (
    <div ref={ref} className="relative w-56">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="input-field flex w-full items-center gap-2 text-left"
      >
        {selected ? (
          <>
            <FlagIcon code={selected.code} />
            <span className="truncate flex-1">{selected.name}</span>
            <span className="text-gray-400 text-xs">{selected.job_count}</span>
          </>
        ) : (
          <span className="text-gray-500">All Countries</span>
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
              All Countries
            </button>
          </li>
          {countries.map((c) => (
            <li key={c.code}>
              <button
                type="button"
                onClick={() => { onChange(c.code); setOpen(false); }}
                className={`flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-gray-100 ${c.code === value ? "bg-primary-50 font-medium" : ""}`}
              >
                <FlagIcon code={c.code} />
                <span className="truncate flex-1">{c.name}</span>
                <span className="text-gray-400 text-xs">{c.job_count}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
