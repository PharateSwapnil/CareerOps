import { useEffect, useState } from "react";
import { apiFetch } from "../lib/api";

interface Job {
  id: number;
  title: string;
  company_name: string;
  location: string | null;
  remote: boolean;
  url: string;
  source_provider: string;
}

interface ScoredJob {
  job: Job;
  score: number;
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [provider, setProvider] = useState("stub");
  const [providers, setProviders] = useState<string[]>(["stub"]);
  const [addedJobIds, setAddedJobIds] = useState<Set<number>>(new Set());

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<ScoredJob[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [similarFor, setSimilarFor] = useState<number | null>(null);
  const [similarResults, setSimilarResults] = useState<ScoredJob[]>([]);

  const loadJobs = async () => {
    const res = await apiFetch("/api/v1/jobs");
    setJobs(await res.json());
  };

  const loadProviders = async () => {
    const res = await apiFetch("/api/v1/jobs/providers");
    setProviders(await res.json());
  };

  const fetchJobs = async () => {
    setLoading(true);
    try {
      await apiFetch(`/api/v1/jobs/fetch?provider_name=${provider}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keywords: ["Engineer"], limit: 25 }),
      });
      await loadJobs();
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
    loadProviders();
  }, []);

  const addToPipeline = async (jobId: number) => {
    const res = await apiFetch("/api/v1/applications", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: jobId }),
    });
    if (res.ok) {
      setAddedJobIds((prev) => new Set(prev).add(jobId));
    }
  };

  const runSemanticSearch = async () => {
    if (!searchQuery) return;
    setSearching(true);
    setSimilarFor(null);
    try {
      const res = await apiFetch("/api/v1/jobs/semantic-search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: searchQuery, limit: 20 }),
      });
      setSearchResults(await res.json());
    } finally {
      setSearching(false);
    }
  };

  const clearSearch = () => {
    setSearchQuery("");
    setSearchResults(null);
  };

  const showSimilar = async (jobId: number) => {
    setSearchResults(null);
    setSimilarFor(jobId);
    const res = await apiFetch(`/api/v1/jobs/${jobId}/similar?limit=10`);
    setSimilarResults(await res.json());
  };

  const renderJobCard = (job: Job, score?: number) => (
    <div className="card" key={job.id}>
      <strong>
        <a href={job.url} target="_blank" rel="noreferrer">
          {job.title}
        </a>
      </strong>
      {score !== undefined && (
        <span style={{ fontSize: 11, opacity: 0.6, marginLeft: 8 }}>
          match: {(score * 100).toFixed(0)}%
        </span>
      )}
      <div>
        {job.company_name} · {job.location ?? "N/A"} {job.remote ? "(Remote)" : ""}
      </div>
      <div>source: {job.source_provider}</div>
      <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
        <button
          style={{ fontSize: 12 }}
          disabled={addedJobIds.has(job.id)}
          onClick={() => addToPipeline(job.id)}
        >
          {addedJobIds.has(job.id) ? "Added to pipeline" : "Add to pipeline"}
        </button>
        <button style={{ fontSize: 12 }} onClick={() => showSimilar(job.id)}>
          Similar roles
        </button>
      </div>
    </div>
  );

  const displayedJobs = searchResults ?? (similarFor ? similarResults : jobs.map((j) => ({ job: j, score: undefined as any })));

  return (
    <div>
      <h2>Jobs</h2>
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <select value={provider} onChange={(e) => setProvider(e.target.value)}>
          {providers.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <button onClick={fetchJobs} disabled={loading}>
          {loading ? "Fetching..." : `Fetch jobs (${provider})`}
        </button>
      </div>

      <div className="card">
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
          Semantic search
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            placeholder="e.g. Snowflake, Databricks, PySpark experience"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ flex: 1 }}
          />
          <button onClick={runSemanticSearch} disabled={searching || !searchQuery}>
            {searching ? "Searching..." : "Search"}
          </button>
          {(searchResults || similarFor) && (
            <button onClick={clearSearch}>Clear</button>
          )}
        </div>
        <div style={{ fontSize: 11, opacity: 0.6, marginTop: 6 }}>
          Matches by meaning, not just keywords — quality depends on the
          configured embedding provider (defaults to a free local one; a
          neural provider like Voyage finds cross-terminology matches more
          reliably).
        </div>
      </div>

      {similarFor && (
        <div style={{ fontSize: 13, marginBottom: 8, opacity: 0.8 }}>
          Showing roles similar to job #{similarFor}
        </div>
      )}

      {jobs.length === 0 && !searchResults && (
        <div className="card">
          <div className="empty-state">
            <div className="empty-icon">💼</div>
            <h3>No jobs yet</h3>
            <p>Pick a provider above and click Fetch to pull in live job listings.</p>
          </div>
        </div>
      )}

      {displayedJobs.map(({ job, score }) => renderJobCard(job, score))}
    </div>
  );
}
