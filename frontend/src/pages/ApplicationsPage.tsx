import { useState } from "react";
import { apiFetch } from "../lib/api";

export default function ApplicationsPage() {
  const [resumeText, setResumeText] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [mode, setMode] = useState<"resume-optimize" | "cover-letter">(
    "resume-optimize"
  );
  const [result, setResult] = useState("");
  const [provider, setProvider] = useState("");
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);

  const runAssist = async () => {
    setLoading(true);
    setResult("");
    setSaved(false);
    try {
      const endpoint =
        mode === "resume-optimize"
          ? "/api/v1/ai/resume-optimize"
          : "/api/v1/ai/cover-letter";
      const res = await apiFetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume_text: resumeText,
          job_description: jobDescription,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        setResult(`Error: ${err.detail ?? res.statusText}`);
        return;
      }
      const data = await res.json();
      setResult(data.content);
      setProvider(data.provider);
    } finally {
      setLoading(false);
    }
  };

  const saveAsResume = async () => {
    const res = await apiFetch("/api/v1/resumes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        label: `AI-optimized (${new Date().toLocaleDateString()})`,
        content: result,
      }),
    });
    if (res.ok) setSaved(true);
  };

  return (
    <div>
      <h2>Applications</h2>
      <div className="card">
        <p>Application pipeline view (dashboard, status tracking) is coming in Milestone 4.</p>
      </div>

      <h3>AI Assist</h3>
      <div className="card">
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <select value={mode} onChange={(e) => setMode(e.target.value as any)}>
            <option value="resume-optimize">Optimize resume</option>
            <option value="cover-letter">Draft cover letter</option>
          </select>
        </div>
        <textarea
          placeholder="Paste your resume text..."
          value={resumeText}
          onChange={(e) => setResumeText(e.target.value)}
          rows={6}
          style={{ width: "100%", marginBottom: 8 }}
        />
        <textarea
          placeholder="Paste the job description..."
          value={jobDescription}
          onChange={(e) => setJobDescription(e.target.value)}
          rows={6}
          style={{ width: "100%", marginBottom: 8 }}
        />
        <button onClick={runAssist} disabled={loading || !resumeText || !jobDescription}>
          {loading ? "Working..." : "Run"}
        </button>

        {result && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 4 }}>
              via {provider}
            </div>
            <pre style={{ whiteSpace: "pre-wrap" }}>{result}</pre>
            {mode === "resume-optimize" && (
              <button style={{ marginTop: 8, fontSize: 12 }} onClick={saveAsResume}>
                {saved ? "Saved to Resumes" : "Save as resume"}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
