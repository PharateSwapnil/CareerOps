import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

interface Command {
  label: string;
  hint: string;
  path: string;
}

const COMMANDS: Command[] = [
  { label: "Go to Dashboard", hint: "Pipeline view", path: "/" },
  { label: "Go to Jobs", hint: "Fetch + semantic search", path: "/jobs" },
  { label: "Go to Saved Searches", hint: "", path: "/saved-searches" },
  { label: "Go to Companies", hint: "Intelligence + enrichment", path: "/companies" },
  { label: "Go to Applications", hint: "AI resume + cover letter assist", path: "/applications" },
  { label: "Go to Resumes", hint: "Versions, diff, rollback", path: "/resumes" },
  { label: "Go to Network", hint: "Contacts + follow-ups", path: "/network" },
  { label: "Go to Profile", hint: "Autofill data", path: "/profile" },
];

export default function CommandPalette({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const navigate = useNavigate();

  const filtered = useMemo(() => {
    if (!query) return COMMANDS;
    const q = query.toLowerCase();
    return COMMANDS.filter(
      (c) => c.label.toLowerCase().includes(q) || c.hint.toLowerCase().includes(q)
    );
  }, [query]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setSelectedIndex(0);
    }
  }, [open]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const runSelected = (index: number) => {
    const command = filtered[index];
    if (!command) return;
    navigate(command.path);
    onClose();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      onClose();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      runSelected(selectedIndex);
    }
  };

  if (!open) return null;

  return (
    <div className="command-palette-backdrop" onClick={onClose}>
      <div className="command-palette" onClick={(e) => e.stopPropagation()}>
        <input
          autoFocus
          placeholder="Type a command or search..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <div className="command-palette-results">
          {filtered.length === 0 && (
            <div style={{ padding: 12, fontSize: 13, opacity: 0.6 }}>No matches</div>
          )}
          {filtered.map((c, i) => (
            <div
              key={c.path}
              className={`command-palette-item ${i === selectedIndex ? "selected" : ""}`}
              onMouseEnter={() => setSelectedIndex(i)}
              onClick={() => runSelected(i)}
            >
              <span>{c.label}</span>
              {c.hint && <span className="command-palette-hint">{c.hint}</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
