import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchJob } from "../api/jobs";
import AdSlot from "../components/AdSlot";
import type { Job } from "../types";

/**
 * Job detail page — full information about a single job listing.
 *
 * Displays:
 *   - Job title, company, location, source, salary
 *   - Full description
 *   - "Visit Company Website" CTA button
 *   - Sidebar ad
 *   - Link back to search results
 */
export default function JobDetail() {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchJob(Number(id));
        setJob(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Job not found");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [id]);

  // ── Loading state ──────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      </div>
    );
  }

  // ── Error state ────────────────────────────────────────────────────
  if (error || !job) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center">
        <svg className="mx-auto h-16 w-16 text-gray-300" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
        </svg>
        <h2 className="mt-4 text-xl font-semibold text-gray-700">Job not found</h2>
        <p className="mt-2 text-gray-500">{error || "This job listing may have been removed."}</p>
        <Link to="/" className="btn-primary mt-6 inline-block">
          Back to search
        </Link>
      </div>
    );
  }

  // ── Formatting helpers ─────────────────────────────────────────────
  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "Unknown";
    return new Date(dateStr).toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }

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
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      {/* ── Breadcrumb ────────────────────────────────────────────── */}
      <Link
        to="/"
        className="mb-6 inline-flex items-center gap-1 text-sm text-primary-600 hover:text-primary-800"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
        </svg>
        Back to search results
      </Link>

      <div className="grid gap-8 lg:grid-cols-[1fr_300px]">
        {/* ── Main Content ────────────────────────────────────────── */}
        <div>
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
            {/* Header */}
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h1 className="text-2xl font-bold text-gray-900 sm:text-3xl">{job.title}</h1>
                <p className="mt-1 text-lg text-gray-600">{job.company}</p>
              </div>
              {job.visa_sponsorship && (
                <span className="rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-700">
                  Visa Sponsorship
                </span>
              )}
            </div>

            {/* Meta info */}
            <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-gray-500">
              {job.location && (
                <span className="flex items-center gap-1">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                  </svg>
                  {job.location}
                </span>
              )}

              <span className={`rounded px-2 py-0.5 text-xs font-medium ${getSourceBadge(job.source)}`}>
                {job.source}
              </span>

              {job.salary_range && (
                <span className="rounded bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-800">
                  {job.salary_range}
                </span>
              )}
            </div>

            {/* Posted / scraped dates */}
            <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-400">
              <span>Posted: {formatDate(job.posted_at)}</span>
              <span>Added: {formatDate(job.scraped_at)}</span>
            </div>

            {/* Description */}
            {job.description && (
              <div className="mt-6 border-t border-gray-100 pt-6">
                <h2 className="mb-3 text-lg font-semibold text-gray-900">Job Description</h2>
                <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-line">
                  {job.description}
                </div>
              </div>
            )}

            {/* Action buttons */}
            <div className="mt-8 flex flex-wrap gap-3 border-t border-gray-100 pt-6">
              <a
                href={job.company_url || job.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-primary"
              >
                <svg className="mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                </svg>
                Visit Company Website
              </a>
              <a
                href={job.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-outline"
              >
                View Original Listing
              </a>
            </div>
          </div>
        </div>

        {/* ── Sidebar — Ad ─────────────────────────────────────────── */}
        <div className="space-y-6">
          <div className="sticky top-24">
            <AdSlot slot="5555555555" format="vertical" className="min-h-[600px]" />
          </div>
        </div>
      </div>
    </div>
  );
}
