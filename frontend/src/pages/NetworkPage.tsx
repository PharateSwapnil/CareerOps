import { useEffect, useState } from "react";

interface Contact {
  id: number;
  full_name: string;
  relationship: string;
  email: string | null;
  linkedin_url: string | null;
  notes: string | null;
  next_follow_up_at: string | null;
}

interface Interaction {
  id: number;
  type: string;
  summary: string;
  occurred_at: string;
}

const RELATIONSHIPS = [
  "recruiter",
  "hiring_manager",
  "referral",
  "cold_outreach",
  "peer",
  "other",
];

export default function NetworkPage() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [followUps, setFollowUps] = useState<Contact[]>([]);
  const [view, setView] = useState<"all" | "follow-ups">("follow-ups");

  const [fullName, setFullName] = useState("");
  const [relationship, setRelationship] = useState("other");
  const [email, setEmail] = useState("");

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [interactions, setInteractions] = useState<Interaction[]>([]);
  const [interactionSummary, setInteractionSummary] = useState("");
  const [followUpDate, setFollowUpDate] = useState("");

  const [msgPurpose, setMsgPurpose] = useState("");
  const [msgResult, setMsgResult] = useState("");
  const [msgLoading, setMsgLoading] = useState(false);

  const loadContacts = async () => {
    const res = await fetch("/api/v1/contacts");
    setContacts(await res.json());
  };

  const loadFollowUps = async () => {
    const res = await fetch("/api/v1/contacts/follow-ups?days_ahead=14");
    setFollowUps(await res.json());
  };

  useEffect(() => {
    loadContacts();
    loadFollowUps();
  }, []);

  const createContact = async () => {
    if (!fullName) return;
    const res = await fetch("/api/v1/contacts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        full_name: fullName,
        relationship,
        email: email || null,
      }),
    });
    if (res.ok) {
      setFullName("");
      setEmail("");
      loadContacts();
      loadFollowUps();
    }
  };

  const openContact = async (contact: Contact) => {
    setSelectedId(contact.id);
    setMsgResult("");
    const res = await fetch(`/api/v1/contacts/${contact.id}/interactions`);
    setInteractions(await res.json());
  };

  const selectedContact = contacts.find((c) => c.id === selectedId) ?? null;

  const logInteraction = async () => {
    if (!selectedId || !interactionSummary) return;
    const res = await fetch(`/api/v1/contacts/${selectedId}/interactions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: "note", summary: interactionSummary }),
    });
    if (res.ok) {
      setInteractionSummary("");
      const listRes = await fetch(`/api/v1/contacts/${selectedId}/interactions`);
      setInteractions(await listRes.json());
    }
  };

  const setFollowUp = async () => {
    if (!selectedId || !followUpDate) return;
    const res = await fetch(`/api/v1/contacts/${selectedId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ next_follow_up_at: new Date(followUpDate).toISOString() }),
    });
    if (res.ok) {
      setFollowUpDate("");
      loadContacts();
      loadFollowUps();
    }
  };

  const generateMessage = async () => {
    if (!selectedContact || !msgPurpose) return;
    setMsgLoading(true);
    try {
      const res = await fetch("/api/v1/ai/networking-message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contact_name: selectedContact.full_name,
          contact_relationship: selectedContact.relationship,
          purpose: msgPurpose,
          channel: "linkedin",
        }),
      });
      const data = await res.json();
      setMsgResult(data.content ?? data.detail ?? "");
    } finally {
      setMsgLoading(false);
    }
  };

  const displayedContacts = view === "follow-ups" ? followUps : contacts;

  return (
    <div>
      <h2>Network</h2>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Add contact</h3>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input
            placeholder="Full name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
          <select value={relationship} onChange={(e) => setRelationship(e.target.value)}>
            {RELATIONSHIPS.map((r) => (
              <option key={r} value={r}>
                {r.replace("_", " ")}
              </option>
            ))}
          </select>
          <input
            placeholder="Email (optional)"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <button onClick={createContact} disabled={!fullName}>
            Add
          </button>
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <button
          style={{ fontWeight: view === "follow-ups" ? 700 : 400 }}
          onClick={() => setView("follow-ups")}
        >
          Follow-ups due ({followUps.length})
        </button>
        <button
          style={{ fontWeight: view === "all" ? 700 : 400 }}
          onClick={() => setView("all")}
        >
          All contacts ({contacts.length})
        </button>
      </div>

      <div style={{ display: "flex", gap: 16 }}>
        <div style={{ flex: 1 }}>
          {displayedContacts.length === 0 && (
            <div className="card">
              <p>
                {view === "follow-ups"
                  ? "No follow-ups due in the next 14 days."
                  : "No contacts yet — add one above."}
              </p>
            </div>
          )}
          {displayedContacts.map((c) => (
            <div
              className="card"
              key={c.id}
              style={{
                cursor: "pointer",
                border: selectedId === c.id ? "1px solid #4a90e2" : undefined,
              }}
              onClick={() => openContact(c)}
            >
              <strong>{c.full_name}</strong>
              <div style={{ fontSize: 12, opacity: 0.7 }}>
                {c.relationship.replace("_", " ")}
                {c.email ? ` · ${c.email}` : ""}
              </div>
              {c.next_follow_up_at && (
                <div style={{ fontSize: 12, marginTop: 4 }}>
                  Follow up: {new Date(c.next_follow_up_at).toLocaleDateString()}
                </div>
              )}
            </div>
          ))}
        </div>

        {selectedContact && (
          <div style={{ flex: 1 }}>
            <div className="card">
              <h3 style={{ marginTop: 0 }}>{selectedContact.full_name}</h3>

              <h4>Set follow-up</h4>
              <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
                <input
                  type="date"
                  value={followUpDate}
                  onChange={(e) => setFollowUpDate(e.target.value)}
                />
                <button onClick={setFollowUp} disabled={!followUpDate}>
                  Save
                </button>
              </div>

              <h4>Log interaction</h4>
              <textarea
                placeholder="e.g. Had a call, discussed the Platform Engineer role..."
                value={interactionSummary}
                onChange={(e) => setInteractionSummary(e.target.value)}
                rows={3}
                style={{ width: "100%", marginBottom: 8 }}
              />
              <button onClick={logInteraction} disabled={!interactionSummary}>
                Log
              </button>

              <h4>History</h4>
              {interactions.length === 0 && <p style={{ fontSize: 13, opacity: 0.7 }}>No interactions logged yet.</p>}
              {interactions.map((i) => (
                <div key={i.id} style={{ fontSize: 13, marginBottom: 8, borderBottom: "1px solid #1f232b", paddingBottom: 8 }}>
                  <div style={{ opacity: 0.6, fontSize: 11 }}>
                    {i.type} · {new Date(i.occurred_at).toLocaleString()}
                  </div>
                  <div>{i.summary}</div>
                </div>
              ))}

              <h4>Draft a message (AI)</h4>
              <input
                placeholder="Purpose (e.g. follow up after phone screen)"
                value={msgPurpose}
                onChange={(e) => setMsgPurpose(e.target.value)}
                style={{ width: "100%", marginBottom: 8 }}
              />
              <button onClick={generateMessage} disabled={msgLoading || !msgPurpose}>
                {msgLoading ? "Drafting..." : "Draft message"}
              </button>
              {msgResult && (
                <pre style={{ whiteSpace: "pre-wrap", marginTop: 8, fontSize: 13 }}>
                  {msgResult}
                </pre>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
