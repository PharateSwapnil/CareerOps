import { useEffect, useRef, useState } from "react";
import { apiFetch } from "../lib/api";

interface Job {
  id: number;
  title: string;
  company_name: string;
  location: string | null;
  remote: boolean;
  url: string;
  source_provider: string;
  description: string | null;
}

interface ScoredJob {
  job: Job;
  score: number;
}

interface ScoredDisplayJob {
  job: Job;
  titleScore: number;   // 0-100
  skillScore: number;   // 0-100
  semanticScore?: number;
}

// ── Matching utilities ──────────────────────────────────────────────────

function titleMatchScore(jobTitle: string, targetTitle: string): number {
  if (!targetTitle.trim()) return 100;
  const jt = jobTitle.toLowerCase();
  const tt = targetTitle.toLowerCase();

  // Exact contains
  if (jt.includes(tt)) return 100;

  // Word overlap
  const jWords = new Set(jt.split(/\W+/).filter(Boolean));
  const tWords = tt.split(/\W+/).filter(Boolean);
  if (tWords.length === 0) return 100;
  const matches = tWords.filter((w) => jWords.has(w) || jt.includes(w)).length;
  return Math.round((matches / tWords.length) * 100);
}

function skillMatchScore(job: Job, userSkills: string[]): number {
  if (userSkills.length === 0) return 100;
  const text = `${job.title} ${job.description || ""}`.toLowerCase();
  const matched = userSkills.filter((s) => text.includes(s.toLowerCase())).length;
  return Math.round((matched / userSkills.length) * 100);
}

// ── Component ────────────────────────────────────────────────────────────

export default function JobsPage() {
  const [allJobs, setAllJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [crawling, setCrawling] = useState(false);
  const [crawlProgress, setCrawlProgress] = useState("");
  const [provider, setProvider] = useState("stub");
  const [providers, setProviders] = useState<string[]>([]);
  const [addedJobIds, setAddedJobIds] = useState<Set<number>>(new Set());
  const [userSkills, setUserSkills] = useState<string[]>([]);
  const [hasResume, setHasResume] = useState(false);

  // Smart filter state
  const [targetTitle, setTargetTitle] = useState("");
  const [titleThreshold, setTitleThreshold] = useState(50);
  const [skillThreshold, setSkillThreshold] = useState(30);
  const [filterMode, setFilterMode] = useState<"all" | "smart">("all");

  // Semantic search
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<ScoredJob[] | null>(null);
  const [searching, setSearching] = useState(false);

  const crawlAbortRef = useRef(false);

  const loadJobs = async () => {
    const res = await apiFetch("/api/v1/jobs");
    setAllJobs(await res.json());
  };

  const loadProviders = async () => {
    const res = await apiFetch("/api/v1/jobs/providers");
    const list: string[] = await res.json();
    setProviders(list);
    if (list.length > 0 && !list.includes(provider)) setProvider(list[0]);
  };

  const loadUserSkills = async () => {
    const res = await apiFetch("/api/v1/me/skills");
    if (res.ok) {
      const data = await res.json();
      setUserSkills(data.skills || []);
      setHasResume(data.has_resume);
    }
  };

  useEffect(() => {
    loadJobs();
    loadProviders();
    loadUserSkills();
  }, []);

  const fetchFromProvider = async () => {
    setLoading(true);
    try {
      await apiFetch(`/api/v1/jobs/fetch?provider_name=${provider}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keywords: [targetTitle || "Engineer"], limit: 25 }),
      });
      await loadJobs();
    } finally { setLoading(false); }
  };

  const crawlAll = async () => {
    const realProviders = providers.filter((p) => p !== "stub");
    if (realProviders.length === 0) {
      setCrawlProgress("No real providers available (only stub).");
      return;
    }
    setCrawling(true);
    crawlAbortRef.current = false;
    let done = 0;
    for (const p of realProviders) {
      if (crawlAbortRef.current) break;
      setCrawlProgress(`Fetching from ${p}… (${done + 1}/${realProviders.length})`);
      try {
        await apiFetch(`/api/v1/jobs/fetch?provider_name=${p}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ keywords: [targetTitle || "Engineer"], limit: 25 }),
        });
      } catch {}
      done++;
    }
    await loadJobs();
    setCrawlProgress(`Done — fetched from ${done} providers.`);
    setCrawling(false);
  };

  const stopCrawl = () => { crawlAbortRef.current = true; };

  const addToPipeline = async (jobId: number) => {
    const res = await apiFetch("/api/v1/applications", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: jobId }),
    });
    if (res.ok) setAddedJobIds((prev) => new Set(prev).add(jobId));
  };

  const runSemanticSearch = async () => {
    if (!searchQuery) return;
    setSearching(true);
    try {
      const res = await apiFetch("/api/v1/jobs/semantic-search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: searchQuery, limit: 30 }),
      });
      setSearchResults(await res.json());
    } finally { setSearching(false); }
  };

  // ── Compute scored+filtered jobs ─────────────────────────────────────

  const scoredJobs: ScoredDisplayJob[] = allJobs.map((job) => ({
    job,
    titleScore: titleMatchScore(job.title, targetTitle),
    skillScore: skillMatchScore(job, userSkills),
  }));

  const displayJobs: ScoredDisplayJob[] = filterMode === "smart"
    ? scoredJobs.filter((j) =>
        j.titleScore >= titleThreshold && j.skillScore >= skillThreshold
      ).sort((a, b) => (b.titleScore + b.skillScore) - (a.titleScore + a.skillScore))
    : scoredJobs;

  const scoreColor = (pct: number) =>
    pct >= 70 ? "var(--success)" : pct >= 40 ? "var(--warning)" : "var(--text-faint)";

  const renderJob = (item: ScoredDisplayJob) => {
    const { job, titleScore, skillScore } = item;
    const added = addedJobIds.has(job.id);
    return (
      <div className="card" key={job.id} style={{ marginBottom: 10 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 2 }}>{job.title}</div>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>
              {job.company_name}
              {job.location ? ` · ${job.location}` : ""}
              {job.remote ? " · Remote" : ""}
            </div>
            {filterMode === "smart" && (
              <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                <span style={{ fontSize: 11 }}>
                  <span style={{ color: "var(--text-faint)" }}>Title </span>
                  <span style={{ fontWeight: 600, color: scoreColor(titleScore) }}>{titleScore}%</span>
                </span>
                {hasResume && (
                  <span style={{ fontSize: 11 }}>
                    <span style={{ color: "var(--text-faint)" }}>Skills </span>
                    <span style={{ fontWeight: 600, color: scoreColor(skillScore) }}>{skillScore}%</span>
                  </span>
                )}
              </div>
            )}
            <div style={{ display: "flex", gap: 6 }}>
              <a href={job.url} target="_blank" rel="noreferrer">
                <button className="ghost" style={{ fontSize: 11, padding: "4px 8px" }}>
                  <i className="ti ti-external-link" aria-hidden="true" /> View
                </button>
              </a>
              <button
                className={added ? "ghost" : "primary"}
                style={{ fontSize: 11, padding: "4px 10px" }}
                disabled={added}
                onClick={() => addToPipeline(job.id)}
              >
                <i className={`ti ${added ? "ti-check" : "ti-plus"}`} aria-hidden="true" />
                {" "}{added ? "In pipeline" : "Add to pipeline"}
              </button>
            </div>
          </div>
          <span className="badge badge-muted" style={{ flexShrink: 0, fontSize: 10 }}>
            {job.source_provider}
          </span>
        </div>
      </div>
    );
  };

  const sourceList = searchResults
    ? searchResults.map((r) => ({
        job: r.job,
        titleScore: titleMatchScore(r.job.title, targetTitle),
        skillScore: skillMatchScore(r.job, userSkills),
      }))
    : displayJobs;

  return (
    <div>
      <div className="page-header"><h2>Jobs</h2></div>

      {/* ── Fetch controls ── */}
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Fetch jobs</h3>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <select value={provider} onChange={(e) => setProvider(e.target.value)} style={{ minWidth: 140 }}>
            {providers.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <input
            placeholder="Job title / keywords"
            value={targetTitle}
            onChange={(e) => setTargetTitle(e.target.value)}
            style={{ flex: 1, minWidth: 160 }}
          />
          <button className="primary" onClick={fetchFromProvider} disabled={loading}>
            <i className="ti ti-download" aria-hidden="true" />
            {" "}{loading ? "Fetching…" : "Fetch"}
          </button>
          <button
            onClick={crawling ? stopCrawl : crawlAll}
            style={{ background: crawling ? "var(--danger-bg)" : undefined, borderColor: crawling ? "var(--danger)" : undefined }}
            disabled={crawling && crawlAbortRef.current}
          >
            <i className={`ti ${crawling ? "ti-player-stop" : "ti-planet"}`} aria-hidden="true" />
            {" "}{crawling ? "Stop crawl" : "Crawl all platforms"}
          </button>
        </div>
        {crawlProgress && (
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 8 }}>
            {crawlProgress}
          </div>
        )}
      </div>

      {/* ── Smart filter ── */}
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <h3 style={{ margin: 0 }}>Smart filter</h3>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              className={filterMode === "all" ? "primary" : "ghost"}
              style={{ fontSize: 12 }}
              onClick={() => setFilterMode("all")}
            >Show all ({allJobs.length})</button>
            <button
              className={filterMode === "smart" ? "primary" : "ghost"}
              style={{ fontSize: 12 }}
              onClick={() => setFilterMode("smart")}
            >
              <i className="ti ti-filter" aria-hidden="true" /> Smart filter ({scoredJobs.filter(j => j.titleScore >= titleThreshold && j.skillScore >= skillThreshold).length})
            </button>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: 6 }}>
              Title match ≥ <span style={{ color: "var(--accent)" }}>{titleThreshold}%</span>
            </label>
            <input
              type="range" min={10} max={100} step={5}
              value={titleThreshold}
              onChange={(e) => setTitleThreshold(Number(e.target.value))}
              style={{ width: "100%" }}
            />
            <div style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 4 }}>
              Matches "{targetTitle || "Engineer"}" against job titles
            </div>
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: 6 }}>
              Skills match ≥ <span style={{ color: "var(--accent)" }}>{skillThreshold}%</span>
            </label>
            <input
              type="range" min={0} max={100} step={5}
              value={skillThreshold}
              onChange={(e) => setSkillThreshold(Number(e.target.value))}
              style={{ width: "100%" }}
            />
            {!hasResume ? (
              <div style={{ fontSize: 11, color: "var(--warning)", marginTop: 4 }}>
                <i className="ti ti-alert-triangle" aria-hidden="true" /> Upload your resume on the Profile page to enable skill matching
              </div>
            ) : (
              <div style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 4 }}>
                Matches {userSkills.length} skills from your resume
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Semantic search ── */}
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Semantic search</h3>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            placeholder="e.g. Snowflake Databricks PySpark"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && runSemanticSearch()}
            style={{ flex: 1 }}
          />
          <button className="primary" onClick={runSemanticSearch} disabled={searching || !searchQuery}>
            {searching ? "Searching…" : "Search"}
          </button>
          {searchResults && (
            <button className="ghost" onClick={() => { setSearchResults(null); setSearchQuery(""); }}>
              Clear
            </button>
          )}
        </div>
      </div>

      {/* ── Job list ── */}
      {sourceList.length === 0 && !loading && (
        <div className="empty-state">
          <div className="empty-icon">💼</div>
          <h3>{allJobs.length === 0 ? "No jobs fetched yet" : "No jobs match your current filters"}</h3>
          <p>
            {allJobs.length === 0
              ? "Pick a provider above and click Fetch to pull in live listings."
              : `Try lowering the title threshold (currently ${titleThreshold}%) or skills threshold (${skillThreshold}%).`}
          </p>
        </div>
      )}

      {searchResults !== null && (
        <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>
          {searchResults.length} semantic matches for "{searchQuery}"
        </div>
      )}

      {sourceList.map((item) => renderJob(item))}
    </div>
  );
}
