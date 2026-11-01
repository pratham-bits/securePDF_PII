import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { documents } from "../api/documents.js";
import FindingsPanel from "../components/FindingsPanel.jsx";
import PdfViewer from "../components/PdfViewer.jsx";
import "./Review.css";

export default function Review() {
  const { id } = useParams();
  const [doc, setDoc] = useState(null);
  const [findings, setFindings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([documents.get(id), documents.findings(id)])
      .then(([loadedDoc, loadedFindings]) => {
        if (cancelled) return;
        setDoc(loadedDoc);
        setFindings(loadedFindings);
      })
      .catch((err) => {
        if (!cancelled)
          setError(err.status === 404 ? "Document not found." : err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  function handleSelect(findingId, scroll) {
    setSelectedId(findingId);
    if (scroll) {
      document
        .getElementById(`box-${findingId}-0`)
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  if (loading) return <p>Loading…</p>;

  const backLink = (
    <Link to="/dashboard" className="btn">
      Back to documents
    </Link>
  );

  if (error) {
    return (
      <div>
        <p className="alert alert--error" role="alert">
          {error}
        </p>
        {backLink}
      </div>
    );
  }

  if (doc.status !== "ready" && doc.status !== "redacted") {
    return (
      <div>
        <h1>Review</h1>
        <p>This document is not ready to review yet (status: {doc.status}).</p>
        {backLink}
      </div>
    );
  }

  const flagged = findings.filter((finding) => finding.score < 0.6).length;

  return (
    <div className="review">
      <header className="review__header">
        <div>
          <h1>Review</h1>
          <p className="review__summary">
            {findings.length} {findings.length === 1 ? "item" : "items"} found
            on {doc.page_count} {doc.page_count === 1 ? "page" : "pages"}
            {flagged > 0 && ` · ${flagged} with low confidence`}. Detection is
            never perfect: check every page yourself.
          </p>
        </div>
        {backLink}
      </header>

      <div className="review__body">
        <PdfViewer
          url={`/api/documents/${id}/original`}
          findings={findings}
          selectedId={selectedId}
          onSelect={handleSelect}
        />
        <aside className="review__panel">
          <FindingsPanel
            findings={findings}
            selectedId={selectedId}
            onSelect={handleSelect}
          />
        </aside>
      </div>
    </div>
  );
}
