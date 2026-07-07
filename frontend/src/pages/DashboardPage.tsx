import { useEffect, useState } from "react";
import { apiFetch } from "../lib/api";

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

interface AutomationSession {
  id: number;
  application_id: number;
  status: string;
  pause_reason: string | null;
  error_message: string | null;
  filled_fields: string | null;
}

export default function DashboardPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [jobs, setJobs] = useState<Record<number, Job>>({});
  const [loading, setLoading] = useState(true);
  const [automationByApp, setAutomationByApp] = useState<Record<number, AutomationSession>>({});

  const load = async () => {
    setLoading(true);
    try {
      const [appsRes, jobsRes] = await Promise.all([
        apiFetch("/api/v1/applications"),
        apiFetch("/api/v1/jobs"),
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
    const res = await apiFetch(`/api/v1/applications/${app.id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: next }),
    });
    if (res.ok) load();
  };

  const reject = async (app: Application) => {
    const res = await apiFetch(`/api/v1/applications/${app.id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "rejected" }),
    });
    if (res.ok) load();
  };

  const startAutomation = async (app: Application) => {
    const res = await apiFetch("/api/v1/automation/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ application_id: app.id }),
    });
    const data = await res.json();
    setAutomationByApp((prev) => ({ ...prev, [app.id]: data }));
  };

  const resumeAutomation = async (app: Application) => {
    const session = automationByApp[app.id];
    if (!session) return;
    const res = await apiFetch(`/api/v1/automation/sessions/${session.id}/resume`, {
      method: "POST",
    });
    const data = await res.json();
    setAutomationByApp((prev) => ({ ...prev, [app.id]: data }));
  };

  const closeAutomation = async (app: Application) => {
    const session = automationByApp[app.id];
    if (!session) return;
    await apiFetch(`/api/v1/automation/sessions/${session.id}`, { method: "DELETE" });
    setAutomationByApp((prev) => {
      const next = { ...prev };
      delete next[app.id];
      return next;
    });
  };

  const activeApps = applications.filter(
    (a) => !["rejected", "withdrawn"].includes(a.status)
  ).length;
  const inInterviews = applications.filter(
    (a) => ["phone_screen", "interviewing"].includes(a.status)
  ).length;
  const offers = applications.filter((a) => a.status === "offer").length;
  const thisWeek = applications.filter((a) => {
    if (!a.applied_at) return false;
    const diff = Date.now() - new Date(a.applied_at).getTime();
    return diff < 7 * 24 * 60 * 60 * 1000;
  }).length;

  return (
    <div>
      <div className="page-header">
        <h2>Dashboard</h2>
      </div>

      <div className="stats-bar">
        <div className="stat-card accent">
          <div className="stat-value">{applications.length}</div>
          <div className="stat-label">Total applications</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{activeApps}</div>
          <div className="stat-label">Active</div>
        </div>
        <div className="stat-card warning">
          <div className="stat-value">{inInterviews}</div>
          <div className="stat-label">Interviewing</div>
        </div>
        <div className="stat-card success">
          <div className="stat-value">{offers}</div>
          <div className="stat-label">Offers</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{thisWeek}</div>
          <div className="stat-label">This week</div>
        </div>
      </div>

      {applications.length === 0 && !loading && (
        <div className="empty-state">
          <div className="empty-icon">📋</div>
          <h3>Your pipeline is empty</h3>
          <p>Fetch jobs from the Jobs page, save the ones you like, and start applying — they'll show up here.</p>
          <a href="/jobs"><button className="primary">Browse jobs →</button></a>
        </div>
      )}

      <div style={{ display: "flex", gap: 12, overflowX: "auto", paddingBottom: 8 }}>
        {STATUS_COLUMNS.map((col) => {
          const colApps = applications.filter((a) => a.status === col.key);
          return (
            <div 
              key={col.key} 
              style={{ minWidth: 220, flex: "0 0 220px" }}
              onDragOver={(e) => {
                e.preventDefault();
                e.currentTarget.style.background = "rgba(var(--accent-rgb), 0.05)";
                e.currentTarget.style.borderRadius = "8px";
              }}
              onDragLeave={(e) => {
                e.currentTarget.style.background = "";
              }}
              onDrop={async (e) => {
                e.preventDefault();
                e.currentTarget.style.background = "";
                try {
                  const data = JSON.parse(e.dataTransfer.getData("application"));
                  if (data.current_status !== col.key) {
                    const res = await apiFetch(`/api/v1/applications/${data.id}/status`, {
                      method: "PATCH",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ status: col.key }),
                    });
                    if (res.ok) load();
                  }
                } catch (err) {
                  console.error("Drop failed:", err);
                }
              }}
            >
              <div style={{
                fontSize: 11,
                fontWeight: 600,
                color: "var(--text-muted)",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                marginBottom: 8,
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "0 2px",
              }}>
                <span>{col.label}</span>
                {colApps.length > 0 && (
                  <span style={{
                    background: "var(--surface-3)",
                    border: "1px solid var(--border)",
                    borderRadius: 20,
                    padding: "1px 7px",
                    fontSize: 11,
                    fontFamily: "var(--font-mono, monospace)",
                  }}>{colApps.length}</span>
                )}
              </div>
              {colApps.length === 0 && (
                <div style={{
                  border: "1px dashed var(--border)",
                  borderRadius: "var(--radius-lg)",
                  padding: "16px 12px",
                  textAlign: "center",
                  fontSize: 11,
                  color: "var(--text-faint)",
                  minHeight: "60px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}>empty</div>
              )}
              {colApps.map((app) => {
                const job = jobs[app.job_id];
                const next = NEXT_STATUS[app.status];
                const automation = automationByApp[app.id];
                return (
                  <div 
                    className={`card interactive stage-${app.status}`} 
                    key={app.id} 
                    style={{ 
                      padding: "12px 14px", 
                      marginBottom: 8,
                      cursor: "grab",
                      transition: "all 0.2s ease"
                    }}
                    draggable
                    onDragStart={(e) => {
                      e.dataTransfer.effectAllowed = "move";
                      e.dataTransfer.setData("application", JSON.stringify({ id: app.id, current_status: app.status }));
                      e.currentTarget.style.opacity = "0.5";
                    }}
                    onDragEnd={(e) => {
                      e.currentTarget.style.opacity = "1";
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: 13, lineHeight: 1.3, marginBottom: 2 }}>
                      {job?.title ?? `Job #${app.job_id}`}
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 10 }}>
                      {job?.company_name ?? ""}
                    </div>
                    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                      {next && (
                        <button style={{ fontSize: 11, padding: "4px 8px" }} onClick={() => advance(app)}>
                          → {STATUS_COLUMNS.find((c) => c.key === next)?.label}
                        </button>
                      )}
                      {col.key !== "rejected" && col.key !== "withdrawn" && (
                        <button className="ghost" style={{ fontSize: 11, padding: "4px 6px", color: "var(--danger)" }} onClick={() => reject(app)}>
                          <i className="ti ti-x" aria-hidden="true" />
                        </button>
                      )}
                    </div>
                    {!automation && col.key !== "rejected" && col.key !== "withdrawn" && (
                      <button
                        className="ghost"
                        style={{ fontSize: 11, marginTop: 6, width: "100%", padding: "5px 8px", color: "var(--text-muted)" }}
                        onClick={() => startAutomation(app)}
                      >
                        <i className="ti ti-bolt" aria-hidden="true" /> Auto-fill
                      </button>
                    )}

                    {automation && (
                      <div style={{
                        marginTop: 8,
                        fontSize: 11,
                        padding: "8px 10px",
                        background: "var(--surface-2)",
                        border: "1px solid var(--border)",
                        borderRadius: "var(--radius)",
                      }}>
                        <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 4 }}>
                          <i className="ti ti-bolt" aria-hidden="true" style={{ color: "var(--accent-2)" }} />
                          {automation.status.replace(/_/g, " ")}
                        </div>
                        {automation.status === "error" && (
                          <div style={{ color: "var(--danger)", marginTop: 4, fontSize: 10 }}>
                            Run <code>playwright install chromium</code>
                          </div>
                        )}
                        {automation.pause_reason && (
                          <div style={{ color: "var(--text-muted)", marginTop: 4 }}>{automation.pause_reason}</div>
                        )}
                        {automation.status === "awaiting_submit" && (
                          <div style={{ color: "var(--success)", marginTop: 4 }}>
                            Review in browser → click Submit yourself
                          </div>
                        )}
                        <div style={{ display: "flex", gap: 4, marginTop: 6 }}>
                          {["paused_auth","paused_captcha","paused_unknown_field"].includes(automation.status) && (
                            <button style={{ fontSize: 10, padding: "3px 7px" }} onClick={() => resumeAutomation(app)}>
                              Resume
                            </button>
                          )}
                          <button className="ghost" style={{ fontSize: 10, padding: "3px 6px" }} onClick={() => closeAutomation(app)}>
                            Close
                          </button>
                        </div>
                      </div>
                    )}
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
