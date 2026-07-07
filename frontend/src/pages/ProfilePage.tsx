import { useEffect, useRef, useState } from "react";
import { apiFetch } from "../lib/api";

interface Profile {
  full_name: string;
  email: string;
  headline: string | null;
  phone: string | null;
  linkedin_url: string | null;
  portfolio_url: string | null;
  base_resume_text: string | null;
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [newSkill, setNewSkill] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    const res = await apiFetch("/api/v1/me");
    const data = await res.json();
    setProfile(data);

    const skillsRes = await apiFetch("/api/v1/me/skills");
    if (skillsRes.ok) {
      const s = await skillsRes.json();
      setSkills(s.skills || []);
    }
  };

  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!profile) return;
    setSaving(true); setSaved(false);
    try {
      const res = await apiFetch("/api/v1/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile),
      });
      if (res.ok) setSaved(true);
    } finally { setSaving(false); }
  };

  const uploadResume = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadMsg("Only PDF files are accepted.");
      return;
    }
    setUploading(true);
    setUploadMsg("");
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await apiFetch("/api/v1/me/upload-resume", { method: "POST", body: form });
      if (res.ok) {
        const data = await res.json();
        setProfile(data);
        const skillsRes = await apiFetch("/api/v1/me/skills");
        if (skillsRes.ok) setSkills((await skillsRes.json()).skills || []);
        setUploadMsg(`Resume uploaded. ${skills.length || "Skills"} extracted.`);
      } else {
        const err = await res.json().catch(() => ({}));
        setUploadMsg(err.detail || "Upload failed.");
      }
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const addSkill = () => {
    const skill = newSkill.trim();
    if (skill && !skills.includes(skill)) {
      setSkills([...skills, skill]);
      setNewSkill("");
    }
  };

  const removeSkill = (skill: string) => {
    setSkills(skills.filter(s => s !== skill));
  };

  if (!profile) return <div style={{ color: "var(--text-muted)", padding: 32 }}>Loading…</div>;

  const field = (key: keyof Profile, label: string, placeholder = "") => (
    <div style={{ marginBottom: 12 }}>
      <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "var(--text-muted)", marginBottom: 4 }}>
        {label}
      </label>
      <input
        value={(profile[key] as string) ?? ""}
        placeholder={placeholder}
        onChange={(e) => setProfile({ ...profile, [key]: e.target.value })}
        style={{ width: "100%" }}
      />
    </div>
  );

  return (
    <div>
      <div className="page-header"><h2>Profile</h2></div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div>
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Contact info</h3>
            <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "0 0 16px 0" }}>
              Used to autofill browser-assisted job applications.
            </p>
            {field("full_name", "Full name")}
            {field("email", "Email")}
            {field("headline", "Headline", "e.g. Senior Data Engineer")}
            {field("phone", "Phone")}
            {field("linkedin_url", "LinkedIn URL", "https://linkedin.com/in/...")}
            {field("portfolio_url", "Portfolio / website")}
            <button className="primary" onClick={save} disabled={saving}>
              {saving ? "Saving…" : saved ? "✓ Saved" : "Save changes"}
            </button>
          </div>
        </div>

        <div>
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Base resume</h3>
            <p style={{ fontSize: 12, color: "var(--text-muted)", margin: "0 0 16px 0" }}>
              Upload your resume PDF. CareerOps++ will extract your skills and use them
              to filter and rank jobs — no third-party service, processed locally.
            </p>

            {profile.base_resume_text ? (
              <div style={{ marginBottom: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                  <span className="badge badge-success">
                    <i className="ti ti-check" /> Resume uploaded
                  </span>
                  <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                    {profile.base_resume_text.length.toLocaleString()} characters extracted
                  </span>
                </div>
                {skills.length > 0 && (
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", marginBottom: 8 }}>
                      Detected skills ({skills.length})
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
                      {skills.map((s) => (
                        <span key={s} className="badge badge-muted" style={{ position: "relative", paddingRight: 20 }}>
                          {s}
                          <button
                            className="ghost"
                            onClick={() => removeSkill(s)}
                            style={{ position: "absolute", right: 2, top: "50%", transform: "translateY(-50%)", padding: 0, fontSize: 12, lineHeight: 1 }}
                            title="Remove skill"
                          >
                            ✕
                          </button>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                <div>
                  <label style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: 6 }}>
                    Add skills manually
                  </label>
                  <div style={{ display: "flex", gap: 6 }}>
                    <input
                      placeholder="e.g. React, Python, AWS"
                      value={newSkill}
                      onChange={(e) => setNewSkill(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && addSkill()}
                      style={{ flex: 1 }}
                    />
                    <button onClick={addSkill} style={{ fontSize: 12 }}>
                      <i className="ti ti-plus" /> Add
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="empty-state" style={{ padding: "20px 16px", marginBottom: 16 }}>
                <div className="empty-icon">📄</div>
                <h3>No resume uploaded yet</h3>
                <p>Upload your PDF to enable skill-based job matching.</p>
              </div>
            )}

            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              style={{ display: "none" }}
              onChange={uploadResume}
            />
            <button
              className="primary"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              style={{ width: "100%" }}
            >
              <i className="ti ti-upload" aria-hidden="true" />
              {" "}{uploading ? "Extracting…" : profile.base_resume_text ? "Replace resume PDF" : "Upload resume PDF"}
            </button>
            {uploadMsg && (
              <div style={{ fontSize: 12, color: uploadMsg.includes("failed") || uploadMsg.includes("Only") ? "var(--danger)" : "var(--success)", marginTop: 8 }}>
                {uploadMsg}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
