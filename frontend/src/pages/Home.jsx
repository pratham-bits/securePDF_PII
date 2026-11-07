import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client.js";
import { useAuth } from "../auth/useAuth.js";
import "./Home.css";

const FEATURES = [
  {
    title: "True redaction",
    text: "The content is removed from the file, not just covered by a black box. Copying the text finds nothing.",
  },
  {
    title: "You stay in control",
    text: "Review every finding before anything changes. Add your own boxes for anything we missed.",
  },
  {
    title: "Private by design",
    text: "Files are encrypted at rest and deleted automatically. We never store the sensitive text we find.",
  },
];

export default function Home() {
  const { user } = useAuth();
  const [apiStatus, setApiStatus] = useState("checking");

  // Development helper: shows whether the dev proxy reaches the backend.
  useEffect(() => {
    api
      .get("/health")
      .then(() => setApiStatus("online"))
      .catch(() => setApiStatus("offline"));
  }, []);

  return (
    <div className="home">
      <section className="home__hero">
        <h1>Redact personal information from PDFs. For real.</h1>
        <p className="home__lead">
          SecurePDF finds Aadhaar and PAN numbers, bank details and more in
          digital and scanned PDFs, lets you review each finding, and removes
          the content from the file.
        </p>
        <div className="home__actions">
          {user ? (
            <Link to="/dashboard" className="btn btn--primary">
              Go to your documents
            </Link>
          ) : (
            <>
              <Link to="/register" className="btn btn--primary">
                Get started
              </Link>
              <Link to="/login" className="btn">
                Log in
              </Link>
            </>
          )}
        </div>
        {import.meta.env.DEV && (
          <p className="home__dev">
            Backend: <strong data-status={apiStatus}>{apiStatus}</strong>
          </p>
        )}
      </section>

      <section className="home__features">
        {FEATURES.map((feature) => (
          <article key={feature.title} className="home__card">
            <h3>{feature.title}</h3>
            <p>{feature.text}</p>
          </article>
        ))}
      </section>
      <p className="home__more">
        Learn <Link to="/why-pii">why personal information matters</Link> and{" "}
        <Link to="/privacy">how we handle your data</Link>.
      </p>
    </div>
  );
}
