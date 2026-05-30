import { useState } from "react";

interface SearchBarProps {
  /** Current search query value. */
  initialValue?: string;
  /** Called when the user submits a search. */
  onSearch: (query: string) => void;
}

/**
 * Search input with a submit button.
 * The user types a keyword and presses Enter or clicks the search icon.
 */
export default function SearchBar({ initialValue = "", onSearch }: SearchBarProps) {
  const [query, setQuery] = useState(initialValue);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSearch(query.trim());
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full max-w-2xl gap-2">
      <div className="relative flex-1">
        <svg
          className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
        </svg>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search jobs, companies, locations..."
          className="input-field pl-10"
        />
      </div>
      <button type="submit" className="btn-primary">
        Search
      </button>
    </form>
  );
}
