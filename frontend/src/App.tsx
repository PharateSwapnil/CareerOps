import { useEffect, useState, ReactNode } from "react";
import { Routes, Route, NavLink, useNavigate, Navigate } from "react-router-dom";
import DashboardPage from "./pages/DashboardPage";
import JobsPage from "./pages/JobsPage";
import ApplicationsPage from "./pages/ApplicationsPage";
import NetworkPage from "./pages/NetworkPage";
import ResumesPage from "./pages/ResumesPage";
import SavedSearchesPage from "./pages/SavedSearchesPage";
import CompaniesPage from "./pages/CompaniesPage";
import ProfilePage from "./pages/ProfilePage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import CommandPalette from "./components/CommandPalette";
import { ThemeProvider, useTheme } from "./lib/theme";
import { AuthProvider, useAuth } from "./lib/auth";

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

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
        Loading...
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function AppShell() {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();
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

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>CareerOps++</h1>
        <nav>
          <div className="section-title">Discover</div>
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            <i className="ti ti-layout-kanban nav-icon" aria-hidden="true" />
            Dashboard
          </NavLink>
          <NavLink to="/jobs" className={({ isActive }) => (isActive ? "active" : "")}>
            <i className="ti ti-briefcase nav-icon" aria-hidden="true" />
            Jobs
          </NavLink>
          <NavLink to="/saved-searches" className={({ isActive }) => (isActive ? "active" : "")}>
            <i className="ti ti-bookmark nav-icon" aria-hidden="true" />
            Saved searches
          </NavLink>
          <NavLink to="/companies" className={({ isActive }) => (isActive ? "active" : "")}>
            <i className="ti ti-building nav-icon" aria-hidden="true" />
            Companies
          </NavLink>

          <div className="section-title" style={{ marginTop: 8 }}>Prepare</div>
          <NavLink to="/applications" className={({ isActive }) => (isActive ? "active" : "")}>
            <i className="ti ti-send nav-icon" aria-hidden="true" />
            Applications
          </NavLink>
          <NavLink to="/resumes" className={({ isActive }) => (isActive ? "active" : "")}>
            <i className="ti ti-file-text nav-icon" aria-hidden="true" />
            Resumes
          </NavLink>
          <NavLink to="/network" className={({ isActive }) => (isActive ? "active" : "")}>
            <i className="ti ti-users nav-icon" aria-hidden="true" />
            Network
          </NavLink>

          <div className="section-title" style={{ marginTop: 8 }}>Account</div>
          <NavLink to="/profile" className={({ isActive }) => (isActive ? "active" : "")}>
            <i className="ti ti-user-circle nav-icon" aria-hidden="true" />
            Profile
          </NavLink>
        </nav>
        <div className="sidebar-footer">
          <div style={{ display: "flex", justifyContent: "space-between", gap: 4 }}>
            <button className="ghost" onClick={() => setPaletteOpen(true)} title="Command palette (⌘K)" style={{ fontSize: 12 }}>
              <span className="kbd">⌘K</span>
            </button>
            <button className="ghost" onClick={toggleTheme} title="Toggle theme" style={{ fontSize: 12 }}>
              <i className={`ti ${theme === "dark" ? "ti-sun" : "ti-moon"}`} aria-hidden="true" />
              {theme === "dark" ? " Light" : " Dark"}
            </button>
          </div>
          <div className="user-row">
            <span className="user-name">{user?.full_name}</span>
            <button className="ghost" onClick={handleLogout} style={{ fontSize: 11, padding: "4px 6px" }} title="Log out">
              <i className="ti ti-logout" aria-hidden="true" />
            </button>
          </div>
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

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/*"
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      />
    </Routes>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </ThemeProvider>
  );
}
