import { useEffect, useState } from "react";

interface Job {
  id: number;
  title: string;
  company_name: string;
  location: string | null;
  remote: boolean;
  url: string;
  source_provider: string;
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [provider, setProvider] = useState("stub");
  const [providers, setProviders] = useState<string[]>(["stub"]);

  const loadJobs = async () => {
    const res = await fetch("/api/v1/jobs");
    setJobs(await res.json());
  };

  const loadProviders = async () => {
    const res = await fetch("/api/v1/jobs/providers");
    setProviders(await res.json());
  };

  const fetchJobs = async () => {
    setLoading(true);
    try {
      await fetch(`/api/v1/jobs/fetch?provider_name=${provider}`, {
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
      {jobs.length === 0 && (
        <div className="card">
          <p>No jobs yet. Pick a provider above and fetch to get started.</p>
        </div>
      )}
      {jobs.map((job) => (
        <div className="card" key={job.id}>
          <strong>
            <a href={job.url} target="_blank" rel="noreferrer">
              {job.title}
            </a>
          </strong>
          <div>
            {job.company_name} · {job.location ?? "N/A"}{" "}
            {job.remote ? "(Remote)" : ""}
          </div>
          <div>source: {job.source_provider}</div>
        </div>
      ))}
    </div>
  );
}
