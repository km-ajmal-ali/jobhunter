import { Link } from "react-router-dom";
import type { Job } from "../types";

interface JobCardProps {
  /** The job listing to display. */
  job: Job;
}

/**
 * Single job card displayed in the search results grid.
 *
 * Shows: title, company, location, source badge, salary (if available),
 * and a link to the detail page.
 */
export default function JobCard({ job }: JobCardProps) {
  /**
   * Format a date string for display.
   * Returns a relative string like "2 days ago" or an absolute date.
   */
  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "Unknown";
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  /** Get source badge color based on the source name. */
  function getSourceBadge(source: string): string {
    const colors: Record<string, string> = {
      linkedin: "bg-blue-100 text-blue-800",
      indeed: "bg-indigo-100 text-indigo-800",
      glassdoor: "bg-green-100 text-green-800",
      h1bgrader: "bg-purple-100 text-purple-800",
      h1base: "bg-orange-100 text-orange-800",
    };
    return colors[source] || "bg-gray-100 text-gray-800";
  }

  return (
    <Link
      to={`/jobs/${job.id}`}
      className="group flex h-full w-full min-w-0 flex-col rounded-lg border border-gray-200 bg-white p-5 shadow-sm transition-all hover:border-primary-300 hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-2">
        <h3
          className="text-base font-semibold text-gray-900 group-hover:text-primary-600 line-clamp-2"
          title={job.title}
        >
          {job.title}
        </h3>
        {job.visa_sponsorship && (
          <span className="shrink-0 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
            Visa
          </span>
        )}
      </div>

      <p className="mt-1 truncate text-sm text-gray-600" title={job.company}>
        {job.company}
      </p>

      {job.location && (
        <p className="mt-1 flex items-center gap-1 truncate text-sm text-gray-500" title={job.location}>
          <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
          </svg>
          <span className="truncate">{job.location}</span>
        </p>
      )}

      <div className="mt-auto flex flex-wrap items-center gap-2 pt-3">
        <span className={`rounded px-2 py-0.5 text-xs font-medium ${getSourceBadge(job.source)}`}>
          {job.source}
        </span>
        {job.salary_range && (
          <span className="rounded bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-800">
            {job.salary_range}
          </span>
        )}
        <span className="ml-auto text-xs text-gray-400">{formatDate(job.posted_at)}</span>
      </div>
    </Link>
  );
}
