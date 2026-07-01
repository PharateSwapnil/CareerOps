import { useEffect, useState } from "react";

interface Application {
  id: number;
  job_id: number;
  status: string;
  notes: string | null;
  applied_at: string | null;
}

interface Job {
  id: number;
  title: string;
  company_name: string;
}

const STATUS_COLUMNS: { key: string; label: string }[] = [
  { key: "saved", label: "Saved" },
  { key: "applied", label: "Applied" },
  { key: "phone_screen", label: "Phone Screen" },
  { key: "interviewing", label: "Interviewing" },
  { key: "offer", label: "Offer" },
  { key: "rejected", label: "Rejected" },
  { key: "withdrawn", label: "Withdrawn" },
];

// Only forward-moving transitions are offered here; the backend still
// enforces the full state machine (including terminal statuses), this is
// just picking a sensible "next step" per column for a simple UI control.
const NEXT_STATUS: Record<string, string | null> = {
  saved: "applied",
  applied: "phone_screen",
  phone_screen: "interviewing",
  interviewing: "offer",
  offer: null,
  rejected: null,
  withdrawn: null,
};

export default function DashboardPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [jobs, setJobs] = useState<Record<number, Job>>({});
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [appsRes, jobsRes] = await Promise.all([
        fetch("/api/v1/applications"),
        fetch("/api/v1/jobs"),
      ]);
      const apps: Application[] = await appsRes.json();
      const jobList: Job[] = await jobsRes.json();
      setApplications(apps);
      setJobs(Object.fromEntries(jobList.map((j) => [j.id, j])));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const advance = async (app: Application) => {
    const next = NEXT_STATUS[app.status];
    if (!next) return;
    const res = await fetch(`/api/v1/applications/${app.id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: next }),
    });
    if (res.ok) load();
  };

  const reject = async (app: Application) => {
    const res = await fetch(`/api/v1/applications/${app.id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "rejected" }),
    });
    if (res.ok) load();
  };

  return (
    <div>
      <h2>Dashboard</h2>
      {applications.length === 0 && !loading && (
        <div className="card">
          <p>
            No applications yet. Fetch some jobs from the Jobs page, then
            create an application via <code>POST /api/v1/applications</code>{" "}
            (dedicated "add to pipeline" UI on the Jobs page is a
            fast-follow) to start tracking it here.
          </p>
        </div>
      )}
      <div style={{ display: "flex", gap: 12, overflowX: "auto" }}>
        {STATUS_COLUMNS.map((col) => {
          const colApps = applications.filter((a) => a.status === col.key);
          return (
            <div key={col.key} style={{ minWidth: 220, flex: "0 0 220px" }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, opacity: 0.8 }}>
                {col.label} ({colApps.length})
              </div>
              {colApps.map((app) => {
                const job = jobs[app.job_id];
                const next = NEXT_STATUS[app.status];
                return (
                  <div className="card" key={app.id} style={{ padding: 12, marginBottom: 8 }}>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>
                      {job?.title ?? `Job #${app.job_id}`}
                    </div>
                    <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 8 }}>
                      {job?.company_name ?? ""}
                    </div>
                    <div style={{ display: "flex", gap: 6 }}>
                      {next && (
                        <button style={{ fontSize: 12 }} onClick={() => advance(app)}>
                          Move to {STATUS_COLUMNS.find((c) => c.key === next)?.label}
                        </button>
                      )}
                      {col.key !== "rejected" && col.key !== "withdrawn" && (
                        <button style={{ fontSize: 12 }} onClick={() => reject(app)}>
                          Reject
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}
