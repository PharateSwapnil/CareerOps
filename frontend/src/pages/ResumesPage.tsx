import { useEffect, useState } from "react";
import { apiFetch } from "../lib/api";

interface Resume {
  id: number;
  label: string;
  content: string;
  version_number: number;
  parent_version_id: number | null;
  created_at: string;
}

// ── Structured Resume Form (uses the designed Swapnil template) ──────────

function StructuredResumeForm({ onCreated }: { onCreated: () => void }) {
  const [saving, setSaving] = useState(false);
  const [label, setLabel] = useState("My Resume");

  // Keep data as a JSON string so the user can see/edit it directly
  const [json, setJson] = useState(() =>
    JSON.stringify(
      {
        contact: {
          name: "YOUR NAME",
          title: "ROLE · SPECIALITY · CLOUD",
          phone: "+91-XXXXXXXXXX",
          email: "you@email.com",
          linkedin: "linkedin.com/in/yourhandle",
          location: "City, Country",
        },
        summary: "Write your professional summary here.",
        skills: [
          { category: "Languages", items: "Python, SQL" },
          { category: "Cloud", items: "AWS (S3, Lambda, EMR, Glue)" },
        ],
        experience: [
          {
            company: "Company Name, City",
            location: "",
            role: "Your Role",
            date_range: "Jan 2024 – Present",
            bullets: [{ text: "Achievement with measurable impact." }],
            projects: [
              {
                name: "Project Name",
                tech_stack: "Python · PySpark · Snowflake",
                bullets: [{ text: "What you built and what it achieved." }],
              },
            ],
          },
        ],
        certifications: ["Your Certification Name"],
        education: [
          {
            degree: "Bachelor of ...",
            institution: "University Name, City",
            date_range: "Jul 2019 – Aug 2022",
          },
        ],
      },
      null,
      2
    )
  );
  const [error, setError] = useState("");

  const save = async () => {
    setError("");
    setSaving(true);
    try {
      const parsed = JSON.parse(json);
      parsed.label = label;
      const res = await apiFetch("/api/v1/resumes/structured", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(parsed),
      });
      if (res.ok) {
        onCreated();
      } else {
        const body = await res.json().catch(() => ({}));
        setError(body.detail || "Failed to create resume");
      }
    } catch {
      setError("Invalid JSON — fix the syntax and try again");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <p style={{ fontSize: 12, opacity: 0.7, margin: "0 0 8px 0" }}>
        Edit the JSON below to fill in your details. The exported PDF will
        use the designed template matching your actual resume layout.
      </p>
      <input
        placeholder="Label"
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        style={{ width: "100%", marginBottom: 8 }}
      />
      <textarea
        value={json}
        onChange={(e) => setJson(e.target.value)}
        rows={22}
        style={{ width: "100%", fontFamily: "var(--font-mono, monospace)", fontSize: 11, marginBottom: 8 }}
      />
      {error && <div style={{ color: "var(--danger)", fontSize: 12, marginBottom: 8 }}>{error}</div>}
      <button className="primary" onClick={save} disabled={saving || !label}>
        {saving ? "Saving..." : "Create with template"}
      </button>
    </div>
  );
}

export default function ResumesPage() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [label, setLabel] = useState("");
  const [content, setContent] = useState("");
  const [useTemplate, setUseTemplate] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [history, setHistory] = useState<Resume[]>([]);
  const [diffText, setDiffText] = useState<string | null>(null);
  const [newVersionContent, setNewVersionContent] = useState("");

  const loadResumes = async () => {
    const res = await apiFetch("/api/v1/resumes");
    setResumes(await res.json());
  };

  useEffect(() => {
    loadResumes();
  }, []);

  const createResume = async () => {
    if (!label || !content) return;
    const res = await apiFetch("/api/v1/resumes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label, content }),
    });
    if (res.ok) {
      setLabel("");
      setContent("");
      loadResumes();
    }
  };

  const openHistory = async (resumeId: number) => {
    setSelectedId(resumeId);
    setDiffText(null);
    const res = await apiFetch(`/api/v1/resumes/${resumeId}/history`);
    setHistory(await res.json());
  };

  const addVersion = async () => {
    if (!selectedId || !newVersionContent) return;
    const res = await apiFetch(`/api/v1/resumes/${selectedId}/versions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        label: history[0]?.label ?? "Untitled",
        content: newVersionContent,
      }),
    });
    if (res.ok) {
      setNewVersionContent("");
      const updated = await res.json();
      openHistory(updated.id);
      loadResumes();
    }
  };

  const rollback = async (versionId: number) => {
    const res = await apiFetch(`/api/v1/resumes/${versionId}/rollback`, {
      method: "POST",
    });
    if (res.ok) {
      const updated = await res.json();
      openHistory(updated.id);
      loadResumes();
    }
  };

  const showDiff = async (fromId: number, toId: number) => {
    const res = await apiFetch(`/api/v1/resumes/${fromId}/diff/${toId}`);
    const data = await res.json();
    setDiffText(data.diff || "(no differences)");
  };

  const downloadResumePdf = async (resumeId: number, label: string) => {
    const res = await apiFetch(`/api/v1/resumes/${resumeId}/export.pdf`);
    if (!res.ok) return;
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${label.replace(/\s+/g, "_")}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div>
      <h2>Resumes</h2>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>New resume</h3>

        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <button
            style={{ fontWeight: useTemplate ? 400 : 700 }}
            onClick={() => setUseTemplate(false)}
          >
            Plain text / markdown
          </button>
          <button
            style={{ fontWeight: useTemplate ? 700 : 400 }}
            onClick={() => setUseTemplate(true)}
          >
            Swapnil template (designed PDF)
          </button>
        </div>

        {!useTemplate ? (
          <>
            <input
              placeholder="Label (e.g. Base resume)"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              style={{ width: "100%", marginBottom: 8 }}
            />
            <textarea
              placeholder="Resume content..."
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={6}
              style={{ width: "100%", marginBottom: 8 }}
            />
            <button onClick={createResume} disabled={!label || !content}>
              Create
            </button>
          </>
        ) : (
          <StructuredResumeForm onCreated={loadResumes} />
        )}
      </div>

      <h3>Your resumes</h3>
      {resumes.length === 0 && (
        <div className="card">
          <p>No resumes yet. Create one above, or generate one with AI Assist on the Applications page.</p>
        </div>
      )}
      {resumes.map((r) => (
        <div className="card" key={r.id}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <strong>{r.label}</strong>
            <span style={{ fontSize: 11, opacity: 0.6 }}>(v{r.version_number})</span>
            {r.content.startsWith("__structured__") && (
              <span style={{ fontSize: 10, color: "var(--accent)", border: "1px solid var(--accent)", borderRadius: 4, padding: "1px 5px" }}>
                designed template
              </span>
            )}
          </div>
          <div style={{ marginTop: 8, display: "flex", gap: 6 }}>
            <button style={{ fontSize: 12 }} onClick={() => openHistory(r.id)}>
              View history
            </button>
            <button style={{ fontSize: 12 }} onClick={() => downloadResumePdf(r.id, r.label)}>
              Download PDF
            </button>
          </div>
        </div>
      ))}

      {selectedId && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Version history</h3>
          {history.map((v, i) => (
            <div
              key={v.id}
              style={{
                padding: 8,
                borderBottom: "1px solid var(--border)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <div style={{ fontWeight: 600 }}>v{v.version_number}</div>
                <div style={{ fontSize: 12, opacity: 0.7 }}>
                  {new Date(v.created_at).toLocaleString()}
                </div>
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                {i > 0 && (
                  <button
                    style={{ fontSize: 12 }}
                    onClick={() => showDiff(history[i - 1].id, v.id)}
                  >
                    Diff vs v{history[i - 1].version_number}
                  </button>
                )}
                <button style={{ fontSize: 12 }} onClick={() => rollback(v.id)}>
                  Roll back to this
                </button>
                <button
                  style={{ fontSize: 12 }}
                  onClick={() => downloadResumePdf(v.id, `${v.version_number}`)}
                >
                  PDF
                </button>
              </div>
            </div>
          ))}

          {diffText && (
            <pre
              style={{
                whiteSpace: "pre-wrap",
                background: "var(--bg)",
                padding: 12,
                borderRadius: 6,
                marginTop: 12,
                fontSize: 12,
              }}
            >
              {diffText}
            </pre>
          )}

          <div style={{ marginTop: 16 }}>
            <h4>Add new version</h4>
            <textarea
              placeholder="Updated content..."
              value={newVersionContent}
              onChange={(e) => setNewVersionContent(e.target.value)}
              rows={5}
              style={{ width: "100%", marginBottom: 8 }}
            />
            <button onClick={addVersion} disabled={!newVersionContent}>
              Save new version
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
