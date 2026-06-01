import { useEffect, useState, useCallback } from "react";
import SearchBar from "../components/SearchBar";
import Filters from "../components/Filters";
import JobCard from "../components/JobCard";
import Pagination from "../components/Pagination";
import AdSlot from "../components/AdSlot";
import { fetchJobs, fetchSources, fetchStats, fetchCountries } from "../api/jobs";
import type { Job, JobSearchParams, SourceInfo, Stats, CountryInfo } from "../types";

/**
 * Home page — the main landing page of JobHunter.
 *
 * Displays:
 *   - Top banner ad (AdSense)
 *   - Search bar
 *   - Filter bar (source, location, visa toggle)
 *   - Paginated grid of job cards
 *   - In-feed ads between job cards
 *   - Footer stats
 */
export default function Home() {
  // ── State ──────────────────────────────────────────────────────────
  const [jobs, setJobs] = useState<Job[]>([]);
  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [countries, setCountries] = useState<CountryInfo[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Search / filter state
  const [query, setQuery] = useState("");
  const [selectedSource, setSelectedSource] = useState("");
  const [selectedCountry, setSelectedCountry] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);

  // ── Data fetching ──────────────────────────────────────────────────

  const loadJobs = useCallback(async (params: JobSearchParams) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchJobs(params);
      setJobs(data.items);
      setTotalPages(data.total_pages);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load jobs");
      setJobs([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMeta = useCallback(async () => {
    try {
      const [sourcesData, statsData, countriesData] = await Promise.all([
        fetchSources(),
        fetchStats(),
        fetchCountries(),
      ]);
      setSources(sourcesData);
      setStats(statsData);
      setCountries(countriesData);
    } catch (err) {
      console.warn("Failed to load metadata:", err);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadJobs({ page: 1, page_size: 20 });
    loadMeta();
  }, [loadJobs, loadMeta]);

  // ── Handlers ───────────────────────────────────────────────────────

  function handleSearch(newQuery: string) {
    setQuery(newQuery);
    setPage(1);
    loadJobs({ q: newQuery || undefined, source: selectedSource || undefined, country: selectedCountry || undefined, page: 1, page_size: 20 });
  }

  function handleFilterChange(filters: { source?: string; country?: string }) {
    if (filters.source !== undefined) setSelectedSource(filters.source);
    if (filters.country !== undefined) setSelectedCountry(filters.country);
    setPage(1);
    loadJobs({
      q: query || undefined,
      source: (filters.source ?? selectedSource) || undefined,
      country: (filters.country ?? selectedCountry) || undefined,
      page: 1,
      page_size: 20,
    });
  }

  function handlePageChange(newPage: number) {
    setPage(newPage);
    loadJobs({ q: query || undefined, source: selectedSource || undefined, country: selectedCountry || undefined, page: newPage, page_size: 20 });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // ── Render ─────────────────────────────────────────────────────────

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      {/* ── Banner Ad ─────────────────────────────────────────────── */}
      <AdSlot slot="1234567890" format="horizontal" className="mb-6" />

      {/* ── Hero Section ──────────────────────────────────────────── */}
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
          Find Jobs with Visa Sponsorship
        </h1>
        <p className="mt-2 text-lg text-gray-600">
          One Search. Thousands of Visas. Our automated scrapers hunt for verified sponsorship opportunities every single day.
        </p>
      </div>

      {/* ── Search ────────────────────────────────────────────────── */}
      <div className="mb-6 flex justify-center">
        <SearchBar initialValue={query} onSearch={handleSearch} />
      </div>

      {/* ── Filters ───────────────────────────────────────────────── */}
      <div className="mb-6">
        <Filters
          sources={sources}
          countries={countries}
          selectedSource={selectedSource}
          selectedCountry={selectedCountry}
          onFilterChange={handleFilterChange}
        />
      </div>

      {/* ── Stats Bar ─────────────────────────────────────────────── */}
      {stats && (
        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-lg bg-white p-3 text-center shadow-sm border border-gray-200">
            <p className="text-2xl font-bold text-primary-600">{stats.total_jobs.toLocaleString()}</p>
            <p className="text-xs text-gray-500">Total Jobs</p>
          </div>
          <div className="rounded-lg bg-white p-3 text-center shadow-sm border border-gray-200">
            <p className="text-2xl font-bold text-green-600">{stats.new_today.toLocaleString()}</p>
            <p className="text-xs text-gray-500">New Today</p>
          </div>
          <div className="rounded-lg bg-white p-3 text-center shadow-sm border border-gray-200">
            <p className="text-2xl font-bold text-purple-600">{stats.sources_online}</p>
            <p className="text-xs text-gray-500">Sources</p>
          </div>
          <div className="rounded-lg bg-white p-3 text-center shadow-sm border border-gray-200">
            <p className="text-sm font-medium text-gray-700">
              {stats.last_scrape_at
                ? new Date(stats.last_scrape_at).toLocaleDateString()
                : "N/A"}
            </p>
            <p className="text-xs text-gray-500">Last Update</p>
          </div>
        </div>
      )}

      {/* ── Job Listings ──────────────────────────────────────────── */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
        </div>
      ) : error ? (
        <div className="rounded-lg bg-red-50 p-6 text-center">
          <p className="text-red-600">{error}</p>
          <button onClick={() => loadJobs({ page: 1 })} className="btn-primary mt-3">
            Retry
          </button>
        </div>
      ) : jobs.length === 0 ? (
        <div className="rounded-lg bg-gray-50 p-12 text-center">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 00-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0112 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 01-.673-.38m0 0A2.18 2.18 0 013 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 013.413-.387m7.5 0V5.25A2.25 2.25 0 0013.5 3h-3a2.25 2.25 0 00-2.25 2.25v.894m7.5 0a48.667 48.667 0 00-7.5 0" />
          </svg>
          <p className="mt-4 text-lg font-medium text-gray-600">No jobs found</p>
          <p className="mt-1 text-sm text-gray-500">Try adjusting your search or filters.</p>
        </div>
      ) : (
        <>
          {/* Job grid — all cards identical width */}
          <div className="grid min-w-0 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {jobs.map((job) => (
              <div key={job.id} className="w-full min-w-0">
                <JobCard job={job} />
              </div>
            ))}
          </div>

          {/* In-feed ad (separate full-width banner outside grid) */}
          {jobs.length > 0 && (
            <div className="mt-4">
              <AdSlot slot="9876543210" format="horizontal" />
            </div>
          )}

          {/* Pagination */}
          <div className="mt-8">
            <Pagination currentPage={page} totalPages={totalPages} onPageChange={handlePageChange} />
          </div>
        </>
      )}
    </div>
  );
}
