import { useEffect, useState } from "react";

interface Resume {
  id: number;
  label: string;
  content: string;
  version_number: number;
  parent_version_id: number | null;
  created_at: string;
}

export default function ResumesPage() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [label, setLabel] = useState("");
  const [content, setContent] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [history, setHistory] = useState<Resume[]>([]);
  const [diffText, setDiffText] = useState<string | null>(null);
  const [newVersionContent, setNewVersionContent] = useState("");

  const loadResumes = async () => {
    const res = await fetch("/api/v1/resumes");
    setResumes(await res.json());
  };

  useEffect(() => {
    loadResumes();
  }, []);

  const createResume = async () => {
    if (!label || !content) return;
    const res = await fetch("/api/v1/resumes", {
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
    const res = await fetch(`/api/v1/resumes/${resumeId}/history`);
    setHistory(await res.json());
  };

  const addVersion = async () => {
    if (!selectedId || !newVersionContent) return;
    const res = await fetch(`/api/v1/resumes/${selectedId}/versions`, {
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
    const res = await fetch(`/api/v1/resumes/${versionId}/rollback`, {
      method: "POST",
    });
    if (res.ok) {
      const updated = await res.json();
      openHistory(updated.id);
      loadResumes();
    }
  };

  const showDiff = async (fromId: number, toId: number) => {
    const res = await fetch(`/api/v1/resumes/${fromId}/diff/${toId}`);
    const data = await res.json();
    setDiffText(data.diff || "(no differences)");
  };

  return (
    <div>
      <h2>Resumes</h2>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>New resume</h3>
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
      </div>

      <h3>Your resumes</h3>
      {resumes.length === 0 && (
        <div className="card">
          <p>No resumes yet. Create one above, or generate one with AI Assist on the Applications page.</p>
        </div>
      )}
      {resumes.map((r) => (
        <div className="card" key={r.id}>
          <strong>{r.label}</strong> (v{r.version_number})
          <div style={{ marginTop: 8, display: "flex", gap: 6 }}>
            <button style={{ fontSize: 12 }} onClick={() => openHistory(r.id)}>
              View history
            </button>
            <a href={`/api/v1/resumes/${r.id}/export.pdf`} download>
              <button style={{ fontSize: 12 }}>Download PDF</button>
            </a>
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
                <a href={`/api/v1/resumes/${v.id}/export.pdf`} download>
                  <button style={{ fontSize: 12 }}>PDF</button>
                </a>
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
