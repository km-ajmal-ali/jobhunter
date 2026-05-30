/**
 * TypeScript type definitions for the JobHunter frontend.
 * Mirrors the backend Pydantic schemas.
 */

/** A single job listing returned by the API. */
export interface Job {
  id: number;
  title: string;
  company: string;
  location: string | null;
  source: string;
  source_url: string;
  company_url: string | null;
  description: string | null;
  salary_range: string | null;
  posted_at: string | null;
  visa_sponsorship: boolean;
  tier: string;
  scraped_at: string;
}

/** Paginated response wrapper for job listings. */
export interface JobListResponse {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/** Status information for a single scrape source. */
export interface SourceInfo {
  name: string;
  tier: string;
  last_scrape: string | null;
  last_status: string | null;
  total_jobs: number;
}

/** Dashboard statistics. */
export interface Stats {
  total_jobs: number;
  new_today: number;
  sources_online: number;
  last_scrape_at: string | null;
}

/** Query parameters for job search. */
export interface JobSearchParams {
  q?: string;
  location?: string;
  source?: string;
  visa_only?: boolean;
  page?: number;
  page_size?: number;
}
