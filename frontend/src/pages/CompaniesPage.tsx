import { useEffect, useState } from "react";

interface Company {
  id: number;
  name: string;
  website: string | null;
  tech_stack: string | null;
  culture_summary: string | null;
  reputation_summary: string | null;
  salary_insights: string | null;
}

interface Job {
  id: number;
  title: string;
  url: string;
  remote: boolean;
  location: string | null;
}

export default function CompaniesPage() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selected, setSelected] = useState<Company | null>(null);
  const [companyJobs, setCompanyJobs] = useState<Job[]>([]);
  const [enriching, setEnriching] = useState(false);
  const [websiteInput, setWebsiteInput] = useState("");

  const load = async () => {
    const res = await fetch("/api/v1/companies");
    setCompanies(await res.json());
  };

  useEffect(() => {
    load();
  }, []);

  const openCompany = async (company: Company) => {
    setSelected(company);
    setWebsiteInput(company.website ?? "");
    const res = await fetch(`/api/v1/companies/${company.id}/jobs`);
    setCompanyJobs(await res.json());
  };

  const saveWebsite = async () => {
    if (!selected) return;
    const res = await fetch(`/api/v1/companies/${selected.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ website: websiteInput }),
    });
    if (res.ok) {
      const updated = await res.json();
      setSelected(updated);
      setCompanies((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    }
  };

  const enrich = async () => {
    if (!selected) return;
    setEnriching(true);
    try {
      const res = await fetch(`/api/v1/companies/${selected.id}/enrich`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const updated = await res.json();
      setSelected(updated);
      setCompanies((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    } finally {
      setEnriching(false);
    }
  };

  return (
    <div>
      <h2>Companies</h2>
      {companies.length === 0 && (
        <div className="card">
          <p>
            No companies yet — companies are created automatically as you
            fetch jobs (each job's employer becomes a Company record you can
            enrich with public data and AI summaries).
          </p>
        </div>
      )}

      <div style={{ display: "flex", gap: 16 }}>
        <div style={{ flex: 1 }}>
          {companies.map((c) => (
            <div
              className="card"
              key={c.id}
              style={{
                cursor: "pointer",
                border: selected?.id === c.id ? "1px solid var(--accent)" : undefined,
              }}
              onClick={() => openCompany(c)}
            >
              <strong>{c.name}</strong>
              {c.tech_stack && (
                <div style={{ fontSize: 12, opacity: 0.7, marginTop: 4 }}>
                  {c.tech_stack}
                </div>
              )}
              {!c.culture_summary && (
                <div style={{ fontSize: 11, opacity: 0.5, marginTop: 4 }}>
                  Not yet enriched
                </div>
              )}
            </div>
          ))}
        </div>

        {selected && (
          <div style={{ flex: 1 }}>
            <div className="card">
              <h3 style={{ marginTop: 0 }}>{selected.name}</h3>

              <div style={{ marginBottom: 10 }}>
                <label style={{ display: "block", fontSize: 12, opacity: 0.7, marginBottom: 4 }}>
                  Website / domain
                </label>
                <div style={{ display: "flex", gap: 6 }}>
                  <input
                    placeholder="e.g. acme.com"
                    value={websiteInput}
                    onChange={(e) => setWebsiteInput(e.target.value)}
                    style={{ flex: 1 }}
                  />
                  <button onClick={saveWebsite}>Save</button>
                </div>
                <div style={{ fontSize: 11, opacity: 0.6, marginTop: 4 }}>
                  Needed for finding contact emails on the Network page.
                </div>
              </div>

              <button onClick={enrich} disabled={enriching}>
                {enriching ? "Enriching..." : "Enrich with public data + AI summary"}
              </button>

              {selected.tech_stack && (
                <div style={{ marginTop: 12 }}>
                  <strong style={{ fontSize: 13 }}>Tech stack (from their own job postings)</strong>
                  <div style={{ fontSize: 13 }}>{selected.tech_stack}</div>
                </div>
              )}

              {selected.culture_summary && (
                <div style={{ marginTop: 12 }}>
                  <strong style={{ fontSize: 13 }}>Culture</strong>
                  <p style={{ fontSize: 13 }}>{selected.culture_summary}</p>
                </div>
              )}

              {selected.reputation_summary && (
                <div style={{ marginTop: 12 }}>
                  <strong style={{ fontSize: 13 }}>Reputation</strong>
                  <p style={{ fontSize: 13 }}>{selected.reputation_summary}</p>
                </div>
              )}

              <div style={{ marginTop: 12 }}>
                <strong style={{ fontSize: 13 }}>Salary insights</strong>
                <p style={{ fontSize: 13, opacity: 0.6 }}>
                  Not available yet — CareerOps++ deliberately doesn't let
                  the AI guess at compensation figures without a real data
                  source behind them, to avoid showing you fabricated
                  numbers.
                </p>
              </div>

              <h4>Open roles ({companyJobs.length})</h4>
              {companyJobs.map((j) => (
                <div key={j.id} style={{ fontSize: 13, marginBottom: 6 }}>
                  <a href={j.url} target="_blank" rel="noreferrer">
                    {j.title}
                  </a>
                  {j.location && ` — ${j.location}`}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
