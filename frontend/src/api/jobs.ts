/**
 * API client for the JobHunter backend.
 *
 * All API calls return typed responses matching the backend schemas.
 * Uses the native fetch API — no additional HTTP client needed.
 */

import type { Job, JobListResponse, JobSearchParams, SourceInfo, Stats } from "../types";

/** Base URL for the API. In dev, this is proxied by Vite. In prod, it's the Nginx path. */
const API_BASE = import.meta.env.VITE_API_BASE || "/api";

/**
 * Build a query string from a params object, skipping undefined/empty values.
 */
function buildQuery(params: Record<string, string | number | boolean | undefined>): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "" && value !== false) {
      searchParams.set(key, String(value));
    }
  }
  return searchParams.toString();
}

/**
 * Fetch paginated job listings with optional search/filter params.
 */
export async function fetchJobs(params: JobSearchParams = {}): Promise<JobListResponse> {
  const query = buildQuery({
    q: params.q,
    location: params.location,
    source: params.source,
    visa_only: params.visa_only,
    page: params.page || 1,
    page_size: params.page_size || 20,
  });

  const response = await fetch(`${API_BASE}/jobs${query ? `?${query}` : ""}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch jobs: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch a single job listing by ID.
 */
export async function fetchJob(id: number): Promise<Job> {
  const response = await fetch(`${API_BASE}/jobs/${id}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch job ${id}: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Fetch all available scrape sources with their status.
 */
export async function fetchSources(): Promise<SourceInfo[]> {
  const response = await fetch(`${API_BASE}/sources`);
  if (!response.ok) {
    throw new Error(`Failed to fetch sources: ${response.statusText}`);
  }
  const data = await response.json();
  return data.sources;
}

/**
 * Fetch dashboard statistics.
 */
export async function fetchStats(): Promise<Stats> {
  const response = await fetch(`${API_BASE}/stats`);
  if (!response.ok) {
    throw new Error(`Failed to fetch stats: ${response.statusText}`);
  }
  return response.json();
}
