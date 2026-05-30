interface PaginationProps {
  /** Current page number (1-indexed). */
  currentPage: number;
  /** Total number of pages available. */
  totalPages: number;
  /** Called when the user clicks a page number or nav button. */
  onPageChange: (page: number) => void;
}

/**
 * Pagination component for navigating through job listing pages.
 *
 * Shows: Previous / [page numbers] / Next
 * Truncates the page list with ellipsis for large page counts.
 */
export default function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null;

  /**
   * Build the array of page numbers to display.
   * Shows first, last, current ± 1, with ellipsis gaps.
   */
  function getPageNumbers(): (number | "ellipsis")[] {
    const pages: (number | "ellipsis")[] = [];
    const delta = 1; // Pages to show around current

    const rangeStart = Math.max(2, currentPage - delta);
    const rangeEnd = Math.min(totalPages - 1, currentPage + delta);

    pages.push(1);

    if (rangeStart > 2) {
      pages.push("ellipsis");
    }

    for (let i = rangeStart; i <= rangeEnd; i++) {
      pages.push(i);
    }

    if (rangeEnd < totalPages - 1) {
      pages.push("ellipsis");
    }

    if (totalPages > 1) {
      pages.push(totalPages);
    }

    return pages;
  }

  return (
    <nav className="flex items-center justify-center gap-1" aria-label="Pagination">
      {/* Previous button */}
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage <= 1}
        className="btn-outline px-3 py-1.5 text-xs disabled:opacity-30"
      >
        Previous
      </button>

      {/* Page numbers */}
      {getPageNumbers().map((page, idx) =>
        page === "ellipsis" ? (
          <span key={`ellipsis-${idx}`} className="px-2 text-gray-400">
            ...
          </span>
        ) : (
          <button
            key={page}
            onClick={() => onPageChange(page)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              page === currentPage
                ? "bg-primary-600 text-white"
                : "text-gray-700 hover:bg-gray-100"
            }`}
          >
            {page}
          </button>
        )
      )}

      {/* Next button */}
      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage >= totalPages}
        className="btn-outline px-3 py-1.5 text-xs disabled:opacity-30"
      >
        Next
      </button>
    </nav>
  );
}
