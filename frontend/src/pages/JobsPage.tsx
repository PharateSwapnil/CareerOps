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

  const loadJobs = async () => {
    const res = await fetch("/api/v1/jobs");
    setJobs(await res.json());
  };

  const fetchStubJobs = async () => {
    setLoading(true);
    try {
      await fetch("/api/v1/jobs/fetch?provider_name=stub", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keywords: ["Engineer"], location: "Remote" }),
      });
      await loadJobs();
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  return (
    <div>
      <h2>Jobs</h2>
      <button onClick={fetchStubJobs} disabled={loading}>
        {loading ? "Fetching..." : "Fetch jobs (stub provider)"}
      </button>
      {jobs.length === 0 && (
        <div className="card">
          <p>No jobs yet. Real provider integrations land in Milestone 2.</p>
        </div>
      )}
      {jobs.map((job) => (
        <div className="card" key={job.id}>
          <strong>{job.title}</strong>
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
