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
  posted_at?: string;
}

interface ScoredJob {
  job: Job;
  score: number;
}

interface ScoredDisplayJob {
  job: Job;
  titleScore: number;
  skillScore: number;
}

// ── Matching utilities ──────────────────────────────────────────────────

function titleMatchScore(jobTitle: string, targetTitles: string[]): number {
  if (targetTitles.length === 0) return 100;
  const jt = jobTitle.toLowerCase();
  
  for (const targetTitle of targetTitles) {
    const tt = targetTitle.toLowerCase().trim();
    if (!tt) continue;
    
    // Exact contains
    if (jt.includes(tt)) return 100;
    
    // Word overlap
    const jWords = new Set(jt.split(/\W+/).filter(Boolean));
    const tWords = tt.split(/\W+/).filter(Boolean);
    if (tWords.length === 0) continue;
    const matches = tWords.filter((w) => jWords.has(w)).length;
    const score = Math.round((matches / tWords.length) * 100);
    if (score > 50) return score;
  }
  
  return 0;
}

function skillMatchScore(job: Job, userSkills: string[]): number {
  if (userSkills.length === 0) return 100;
  const text = `${job.title} ${job.description || ""}`.toLowerCase();
  const matched = userSkills.filter((s) => text.includes(s.toLowerCase())).length;
  return Math.round((matched / userSkills.length) * 100);
}

function isRecentJob(postedAt: string | undefined, daysAgo: number): boolean {
  if (!postedAt) return true;
  const posted = new Date(postedAt).getTime();
  const cutoff = Date.now() - daysAgo * 24 * 60 * 60 * 1000;
  return posted >= cutoff;
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
  const [targetTitles, setTargetTitles] = useState<string[]>([]);
  const [titleInput, setTitleInput] = useState("");
  const [selectedProviders, setSelectedProviders] = useState<Set<string>>(new Set()); // For filtering results
  const [daysFilter, setDaysFilter] = useState(2); // Default: last 2 days
  const [filterMode, setFilterMode] = useState<"all" | "smart">("all");

  // Semantic search
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<ScoredJob[] | null>(null);
  const [searching, setSearching] = useState(false);

  const crawlAbortRef = useRef(false);

  const TITLE_THRESHOLD = 75;
  const SKILL_THRESHOLD = 60;

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
      const keywords = targetTitles.length > 0 ? targetTitles : ["Engineer"];
      await apiFetch(`/api/v1/jobs/fetch?provider_name=${provider}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ keywords, limit: 25 }),
      });
      await loadJobs();
    } finally {
      setLoading(false);
    }
  };

  const crawlAll = async () => {
    const realProviders = providers.filter((p) => p !== "stub");
    if (realProviders.length === 0) {
      setCrawlProgress("No real providers available.");
      return;
    }
    setCrawling(true);
    crawlAbortRef.current = false;
    let done = 0;
    const keywords = targetTitles.length > 0 ? targetTitles : ["Engineer"];
    
    for (const p of realProviders) {
      if (crawlAbortRef.current) break;
      setCrawlProgress(`Fetching from ${p}… (${done + 1}/${realProviders.length})`);
      try {
        await apiFetch(`/api/v1/jobs/fetch?provider_name=${p}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ keywords, limit: 25 }),
        });
      } catch {}
      done++;
    }
    await loadJobs();
    setCrawlProgress(`Done — fetched from ${done} providers.`);
    setCrawling(false);
  };

  const stopCrawl = () => {
    crawlAbortRef.current = true;
  };

  const addTitleToFilter = () => {
    const title = titleInput.trim();
    if (title && !targetTitles.includes(title)) {
      setTargetTitles([...targetTitles, title]);
      setTitleInput("");
    }
  };

  const removeTitleFilter = (title: string) => {
    setTargetTitles(targetTitles.filter(t => t !== title));
  };

  const toggleProviderFilter = (p: string) => {
    const newSet = new Set(selectedProviders);
    if (newSet.has(p)) {
      newSet.delete(p);
    } else {
      newSet.add(p);
    }
    setSelectedProviders(newSet);
  };

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
    } finally {
      setSearching(false);
    }
  };

  // ── Compute filtered jobs ─────────────────────────────────────────────

  let filteredJobs = allJobs;

  // Filter by date (last N days)
  filteredJobs = filteredJobs.filter(j => isRecentJob(j.posted_at, daysFilter));

  // Filter by selected providers
  if (selectedProviders.size > 0) {
    filteredJobs = filteredJobs.filter(j => selectedProviders.has(j.source_provider));
  }

  const scoredJobs: ScoredDisplayJob[] = filteredJobs.map((job) => ({
    job,
    titleScore: titleMatchScore(job.title, targetTitles),
    skillScore: skillMatchScore(job, userSkills),
  }));

  const displayJobs: ScoredDisplayJob[] = filterMode === "smart"
    ? scoredJobs
        .filter((j) => j.titleScore >= TITLE_THRESHOLD && j.skillScore >= SKILL_THRESHOLD)
        .sort((a, b) => (b.titleScore + b.skillScore) - (a.titleScore + a.skillScore))
    : scoredJobs;

  const smartFilterCount = scoredJobs.filter(
    j => j.titleScore >= TITLE_THRESHOLD && j.skillScore >= SKILL_THRESHOLD
  ).length;

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
              <button 
                className="ghost" 
                style={{ fontSize: 11, padding: "4px 8px" }}
                onClick={() => job.url && window.open(job.url, "_blank")}
                disabled={!job.url}
              >
                <i className="ti ti-external-link" aria-hidden="true" /> View
              </button>
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
        titleScore: titleMatchScore(r.job.title, targetTitles),
        skillScore: skillMatchScore(r.job, userSkills),
      }))
    : displayJobs;

  return (
    <div>
      <div className="page-header"><h2>Jobs</h2></div>

      {/* ── Smart Filter Controls (Before Fetch) ── */}
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Smart job search</h3>
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: 6 }}>
            Target job titles (add multiple)
          </label>
          <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
            <input
              placeholder="e.g. Senior Engineer, Data Scientist"
              value={titleInput}
              onChange={(e) => setTitleInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addTitleToFilter()}
              style={{ flex: 1 }}
            />
            <button onClick={addTitleToFilter} style={{ fontSize: 12 }}>
              <i className="ti ti-plus" /> Add
            </button>
          </div>
          {targetTitles.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
              {targetTitles.map((t) => (
                <span key={t} className="badge badge-accent" style={{ position: "relative", paddingRight: 20 }}>
                  {t}
                  <button
                    className="ghost"
                    onClick={() => removeTitleFilter(t)}
                    style={{ position: "absolute", right: 2, top: "50%", transform: "translateY(-50%)", padding: 0, fontSize: 12, lineHeight: 1 }}
                    title="Remove title"
                  >
                    ✕
                  </button>
                </span>
              ))}
            </div>
          )}
          <div style={{ fontSize: 11, color: "var(--text-faint)" }}>
            Thresholds: Title ≥ 75%, Skills ≥ 60% (auto-applied when filtering)
          </div>
        </div>
      </div>

      {/* ── Fetch controls ── */}
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Fetch jobs</h3>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <select value={provider} onChange={(e) => setProvider(e.target.value)} style={{ minWidth: 140 }}>
            {providers.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <input
            placeholder="Job title / keywords (or use targets above)"
            value={titleInput}
            onChange={(e) => setTitleInput(e.target.value)}
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

      {/* ── Filter Results ── */}
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Filter results</h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 12 }}>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: 6 }}>
              Posted within last: <span style={{ color: "var(--accent)" }}>{daysFilter} days</span>
            </label>
            <input
              type="range" min={1} max={30} step={1}
              value={daysFilter}
              onChange={(e) => setDaysFilter(Number(e.target.value))}
              style={{ width: "100%" }}
            />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: 6 }}>
              Job portals ({selectedProviders.size > 0 ? selectedProviders.size : "all"} selected)
            </label>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {providers.filter(p => p !== "stub").map((p) => (
                <button
                  key={p}
                  className={selectedProviders.has(p) ? "primary" : "ghost"}
                  style={{ fontSize: 11, padding: "4px 8px" }}
                  onClick={() => toggleProviderFilter(p)}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            className={filterMode === "all" ? "primary" : "ghost"}
            style={{ fontSize: 12 }}
            onClick={() => setFilterMode("all")}
          >Show all ({filteredJobs.length})</button>
          <button
            className={filterMode === "smart" ? "primary" : "ghost"}
            style={{ fontSize: 12 }}
            onClick={() => setFilterMode("smart")}
          >
            <i className="ti ti-filter" aria-hidden="true" /> Smart filter ({smartFilterCount})
          </button>
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
          <h3>{filteredJobs.length === 0 ? "No jobs found" : "No jobs match your filters"}</h3>
          <p>
            {filteredJobs.length === 0
              ? "Fetch jobs from providers above using your target titles."
              : `Try adjusting date range (currently ${daysFilter} days), adding more providers, or lowering match thresholds.`}
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
