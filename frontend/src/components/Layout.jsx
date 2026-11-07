import { Link, Outlet } from "react-router-dom";

import { useAuth } from "../auth/useAuth.js";
import "./Layout.css";

export default function Layout() {
  const { user, loading } = useAuth();

  return (
    <div className="layout">
      <header className="layout__header">
        <div className="layout__inner">
          <Link to="/" className="brand" aria-label="SecurePDF home">
            <span className="brand__mark" aria-hidden="true" />
            SecurePDF
          </Link>
          <nav className="layout__nav">
            <Link to="/">Home</Link>
            {!loading && user && (
              <>
                <Link to="/dashboard">Dashboard</Link>
                <Link to="/profile">Profile</Link>
              </>
            )}
            {!loading && !user && (
              <>
                <Link to="/login">Log in</Link>
                <Link to="/register" className="btn btn--primary layout__cta">
                  Get started
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="layout__main">
        <Outlet />
      </main>
      <footer className="layout__footer">
        <div className="layout__inner">
          <span>
            An assistive tool: always review the result before sharing a
            document.
          </span>
          <nav className="layout__footer-nav" aria-label="Information">
            <Link to="/why-pii">Why PII matters</Link>
            <Link to="/privacy">How we handle your data</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
