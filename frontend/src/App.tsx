import { useEffect, useState } from "react";
import { Routes, Route, NavLink, useNavigate } from "react-router-dom";
import DashboardPage from "./pages/DashboardPage";
import JobsPage from "./pages/JobsPage";
import ApplicationsPage from "./pages/ApplicationsPage";
import NetworkPage from "./pages/NetworkPage";
import ResumesPage from "./pages/ResumesPage";
import SavedSearchesPage from "./pages/SavedSearchesPage";
import CompaniesPage from "./pages/CompaniesPage";
import ProfilePage from "./pages/ProfilePage";
import CommandPalette from "./components/CommandPalette";
import { ThemeProvider, useTheme } from "./lib/theme";

// Single-key "go to" shortcuts, active whenever focus isn't in a text
// input - a lighter-weight complement to the command palette for the most
// common navigation targets.
const GOTO_SHORTCUTS: Record<string, string> = {
  d: "/",
  j: "/jobs",
  a: "/applications",
  r: "/resumes",
  n: "/network",
  c: "/companies",
};

function AppShell() {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const isMeta = e.metaKey || e.ctrlKey;
      const target = e.target as HTMLElement;
      const isTyping =
        target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;

      if (isMeta && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((open) => !open);
        return;
      }

      if (!isTyping && !isMeta && GOTO_SHORTCUTS[e.key]) {
        navigate(GOTO_SHORTCUTS[e.key]);
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [navigate]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>CareerOps++</h1>
        <nav>
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Dashboard
          </NavLink>
          <NavLink to="/jobs" className={({ isActive }) => (isActive ? "active" : "")}>
            Jobs
          </NavLink>
          <NavLink to="/saved-searches" className={({ isActive }) => (isActive ? "active" : "")}>
            Saved Searches
          </NavLink>
          <NavLink to="/companies" className={({ isActive }) => (isActive ? "active" : "")}>
            Companies
          </NavLink>
          <NavLink to="/applications" className={({ isActive }) => (isActive ? "active" : "")}>
            Applications
          </NavLink>
          <NavLink to="/resumes" className={({ isActive }) => (isActive ? "active" : "")}>
            Resumes
          </NavLink>
          <NavLink to="/network" className={({ isActive }) => (isActive ? "active" : "")}>
            Network
          </NavLink>
          <NavLink to="/profile" className={({ isActive }) => (isActive ? "active" : "")}>
            Profile
          </NavLink>
        </nav>
        <div className="sidebar-footer">
          <button onClick={() => setPaletteOpen(true)} title="Command palette">
            <span className="kbd">⌘K</span>
          </button>
          <button onClick={toggleTheme} title="Toggle theme">
            {theme === "dark" ? "☀︎ Light" : "☾ Dark"}
          </button>
        </div>
      </aside>
      <main className="main-content">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/saved-searches" element={<SavedSearchesPage />} />
          <Route path="/companies" element={<CompaniesPage />} />
          <Route path="/applications" element={<ApplicationsPage />} />
          <Route path="/resumes" element={<ResumesPage />} />
          <Route path="/network" element={<NetworkPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>
      </main>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AppShell />
    </ThemeProvider>
  );
}
