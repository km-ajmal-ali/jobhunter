import { SourceInfo } from "../types";

interface FiltersProps {
  /** Available sources to filter by. */
  sources: SourceInfo[];
  /** Currently selected source. */
  selectedSource: string;
  /** Current location filter text. */
  location: string;
  /** Whether visa-only filter is active. */
  visaOnly: boolean;
  /** Called when any filter changes. */
  onFilterChange: (filters: { source?: string; location?: string; visa_only?: boolean }) => void;
}

/**
 * Filter bar with source dropdown, location input, and visa-only toggle.
 */
export default function Filters({
  sources,
  selectedSource,
  location,
  visaOnly,
  onFilterChange,
}: FiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Source filter */}
      <select
        value={selectedSource}
        onChange={(e) => onFilterChange({ source: e.target.value })}
        className="input-field w-40"
      >
        <option value="">All Sources</option>
        {sources.map((s) => (
          <option key={s.name} value={s.name}>
            {s.name.charAt(0).toUpperCase() + s.name.slice(1)} ({s.total_jobs})
          </option>
        ))}
      </select>

      {/* Location filter */}
      <input
        type="text"
        value={location}
        onChange={(e) => onFilterChange({ location: e.target.value })}
        placeholder="Location..."
        className="input-field w-44"
      />

      {/* Visa sponsorship toggle */}
      <label className="flex cursor-pointer items-center gap-2 text-sm text-gray-700">
        <input
          type="checkbox"
          checked={visaOnly}
          onChange={(e) => onFilterChange({ visa_only: e.target.checked })}
          className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
        />
        Visa sponsorship only
      </label>
    </div>
  );
}
