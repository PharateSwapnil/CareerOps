import { Routes, Route, Link } from "react-router-dom";
import DashboardPage from "./pages/DashboardPage";
import JobsPage from "./pages/JobsPage";
import ApplicationsPage from "./pages/ApplicationsPage";
import NetworkPage from "./pages/NetworkPage";

export default function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>CareerOps++</h1>
        <nav>
          <Link to="/">Dashboard</Link>
          <Link to="/jobs">Jobs</Link>
          <Link to="/applications">Applications</Link>
          <Link to="/network">Network</Link>
        </nav>
      </aside>
      <main className="main-content">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/applications" element={<ApplicationsPage />} />
          <Route path="/network" element={<NetworkPage />} />
        </Routes>
      </main>
    </div>
  );
}
