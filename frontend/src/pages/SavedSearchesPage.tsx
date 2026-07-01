import { useEffect, useState } from "react";

interface SavedSearch {
  id: number;
  name: string;
  query_text: string;
  embedding_provider: string;
  created_at: string;
}

interface Job {
  id: number;
  title: string;
  company_name: string;
  location: string | null;
  remote: boolean;
  url: string;
}

interface ScoredJob {
  job: Job;
  score: number;
}

export default function SavedSearchesPage() {
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [name, setName] = useState("");
  const [queryText, setQueryText] = useState("");
  const [activeMatches, setActiveMatches] = useState<{ id: number; results: ScoredJob[] } | null>(
    null
  );

  const load = async () => {
    const res = await fetch("/api/v1/saved-searches");
    setSearches(await res.json());
  };

  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    if (!name || !queryText) return;
    const res = await fetch("/api/v1/saved-searches", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, query_text: queryText }),
    });
    if (res.ok) {
      setName("");
      setQueryText("");
      load();
    }
  };

  const remove = async (id: number) => {
    const res = await fetch(`/api/v1/saved-searches/${id}`, { method: "DELETE" });
    if (res.ok) {
      if (activeMatches?.id === id) setActiveMatches(null);
      load();
    }
  };

  const viewMatches = async (id: number) => {
    const res = await fetch(`/api/v1/saved-searches/${id}/matches`);
    setActiveMatches({ id, results: await res.json() });
  };

  return (
    <div>
      <h2>Saved Searches</h2>
      <div className="card">
        <h3 style={{ marginTop: 0 }}>New saved search</h3>
        <input
          placeholder="Name (e.g. Data platform roles)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={{ width: "100%", marginBottom: 8 }}
        />
        <input
          placeholder="What are you looking for? (e.g. Snowflake, Databricks, PySpark)"
          value={queryText}
          onChange={(e) => setQueryText(e.target.value)}
          style={{ width: "100%", marginBottom: 8 }}
        />
        <button onClick={create} disabled={!name || !queryText}>
          Save
        </button>
      </div>

      {searches.length === 0 && (
        <div className="card">
          <p>
            No saved searches yet. These re-run semantic matching against
            your job database any time you check back — useful for tracking
            a role type over time as new postings come in.
          </p>
        </div>
      )}

      {searches.map((s) => (
        <div className="card" key={s.id}>
          <strong>{s.name}</strong>
          <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 8 }}>
            "{s.query_text}" · via {s.embedding_provider}
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <button style={{ fontSize: 12 }} onClick={() => viewMatches(s.id)}>
              View matches
            </button>
            <button style={{ fontSize: 12 }} onClick={() => remove(s.id)}>
              Delete
            </button>
          </div>
        </div>
      ))}

      {activeMatches && (
        <div>
          <h3>Matches</h3>
          {activeMatches.results.length === 0 && (
            <div className="card">
              <p>No matches yet — try ingesting more jobs first.</p>
            </div>
          )}
          {activeMatches.results.map(({ job, score }) => (
            <div className="card" key={job.id}>
              <strong>
                <a href={job.url} target="_blank" rel="noreferrer">
                  {job.title}
                </a>
              </strong>
              <span style={{ fontSize: 11, opacity: 0.6, marginLeft: 8 }}>
                match: {(score * 100).toFixed(0)}%
              </span>
              <div>
                {job.company_name} · {job.location ?? "N/A"} {job.remote ? "(Remote)" : ""}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
