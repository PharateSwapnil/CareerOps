import { useEffect, useState } from "react";
import { apiFetch } from "../lib/api";

interface Profile {
  full_name: string;
  email: string;
  headline: string | null;
  phone: string | null;
  linkedin_url: string | null;
  portfolio_url: string | null;
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const load = async () => {
    const res = await apiFetch("/api/v1/me");
    setProfile(await res.json());
  };

  useEffect(() => {
    load();
  }, []);

  const save = async () => {
    if (!profile) return;
    setSaving(true);
    setSaved(false);
    try {
      const res = await apiFetch("/api/v1/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile),
      });
      if (res.ok) setSaved(true);
    } finally {
      setSaving(false);
    }
  };

  if (!profile) return <div>Loading...</div>;

  const field = (key: keyof Profile, label: string, placeholder = "") => (
    <div style={{ marginBottom: 10 }}>
      <label style={{ display: "block", fontSize: 12, opacity: 0.7, marginBottom: 4 }}>
        {label}
      </label>
      <input
        value={profile[key] ?? ""}
        placeholder={placeholder}
        onChange={(e) => setProfile({ ...profile, [key]: e.target.value })}
        style={{ width: "100%" }}
      />
    </div>
  );

  return (
    <div>
      <h2>Profile</h2>
      <div className="card">
        <p style={{ fontSize: 13, opacity: 0.8 }}>
          This information is used to autofill browser-assisted job
          applications (see the Dashboard) — nothing here is shared or sent
          anywhere except into forms you're actively applying to yourself.
        </p>
        {field("full_name", "Full name")}
        {field("email", "Email")}
        {field("headline", "Headline", "e.g. Senior Backend Engineer")}
        {field("phone", "Phone")}
        {field("linkedin_url", "LinkedIn URL", "https://linkedin.com/in/...")}
        {field("portfolio_url", "Portfolio / website URL")}
        <button onClick={save} disabled={saving}>
          {saving ? "Saving..." : saved ? "Saved" : "Save"}
        </button>
      </div>
    </div>
  );
}
