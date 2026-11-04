import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { documents } from "../api/documents.js";
import ConfirmDialog from "../components/ConfirmDialog.jsx";
import FindingsPanel from "../components/FindingsPanel.jsx";
import PdfViewer from "../components/PdfViewer.jsx";
import RedactionPanel from "../components/RedactionPanel.jsx";
import { saveBlob } from "../lib/download.js";
import { entityLabel } from "../lib/entities.js";
import "./Review.css";

const POLL_MS = 2000;

export default function Review() {
  const { id } = useParams();
  const [doc, setDoc] = useState(null);
  const [findings, setFindings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [selectedId, setSelectedId] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [drawMode, setDrawMode] = useState(false);
  const [pendingConfirm, setPendingConfirm] = useState(null);
  const [starting, setStarting] = useState(false);
  const [downloading, setDownloading] = useState(false);

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

  // While the server redacts and verifies, check on it regularly.
  const redacting = doc?.status === "redacting";
  useEffect(() => {
    if (!redacting) return undefined;
    const timer = setInterval(() => {
      documents
        .get(id)
        .then(setDoc)
        .catch(() => {});
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [redacting, id]);

  function handleSelect(findingId, scroll) {
    setSelectedId(findingId);
    if (scroll) {
      document
        .getElementById(`box-${findingId}-0`)
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  // Runs a change on the server. A change to a redacted document makes the server
  // discard its output, so the document is reloaded to show the new status.
  async function mutate(action) {
    setActionError("");
    try {
      await action();
      if (doc.status === "redacted") setDoc(await documents.get(id));
    } catch (err) {
      setActionError(err.message);
    }
  }

  function applyDecision(finding, decision, confirmOverride = false) {
    setBusyId(finding.id);
    return mutate(async () => {
      const updated = await documents.setDecision(
        id,
        finding.id,
        decision,
        confirmOverride,
      );
      setFindings((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
    }).finally(() => setBusyId(null));
  }

  function handleToggle(finding) {
    const next = finding.decision === "redact" ? "keep" : "redact";
    if (next === "keep" && finding.tier === "mandatory") {
      setPendingConfirm(finding); // ask first; the server also insists on it
      return;
    }
    applyDecision(finding, next);
  }

  function confirmKeep() {
    const finding = pendingConfirm;
    setPendingConfirm(null);
    applyDecision(finding, "keep", true);
  }

  function handleDraw(box) {
    return mutate(async () => {
      const created = await documents.addBox(id, box);
      setFindings((current) => [...current, created]);
      setSelectedId(created.id);
    });
  }

  function handleRemove(finding) {
    setBusyId(finding.id);
    return mutate(async () => {
      await documents.removeBox(id, finding.id);
      setFindings((current) =>
        current.filter((item) => item.id !== finding.id),
      );
      setSelectedId((current) => (current === finding.id ? null : current));
    }).finally(() => setBusyId(null));
  }

  async function handleRedact() {
    setActionError("");
    setStarting(true);
    setDrawMode(false);
    try {
      setDoc(await documents.redact(id));
    } catch (err) {
      setActionError(err.message);
    } finally {
      setStarting(false);
    }
  }

  async function handleDownload() {
    setActionError("");
    setDownloading(true);
    try {
      const blob = await documents.downloadRedacted(id);
      saveBlob(blob, `redacted-${id.slice(0, 8)}.pdf`);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setDownloading(false);
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

  const reviewable = ["ready", "redacting", "redacted"].includes(doc.status);
  if (!reviewable) {
    return (
      <div>
        <h1>Review</h1>
        <p>This document is not ready to review yet (status: {doc.status}).</p>
        {backLink}
      </div>
    );
  }

  const locked = doc.status === "redacting";
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

      <RedactionPanel
        doc={doc}
        findings={findings}
        starting={starting}
        downloading={downloading}
        onRedact={handleRedact}
        onDownload={handleDownload}
      />

      <div className="review__toolbar">
        <button
          type="button"
          className={`btn btn--small${drawMode ? " btn--primary" : ""}`}
          aria-pressed={drawMode}
          disabled={locked}
          onClick={() => setDrawMode((on) => !on)}
        >
          {drawMode ? "Done drawing" : "Add a box"}
        </button>
        <span className="review__hint">
          {drawMode
            ? "Drag over anything we missed on the page."
            : "Missed something? Draw your own box."}
        </span>
      </div>

      {actionError && (
        <p className="alert alert--error" role="alert">
          {actionError}
        </p>
      )}

      <div className="review__body">
        <PdfViewer
          url={`/api/documents/${id}/original`}
          findings={findings}
          selectedId={selectedId}
          onSelect={handleSelect}
          drawMode={drawMode && !locked}
          onDraw={handleDraw}
        />
        <aside className="review__panel">
          <FindingsPanel
            findings={findings}
            selectedId={selectedId}
            busyId={busyId}
            locked={locked}
            onSelect={handleSelect}
            onToggle={handleToggle}
            onRemove={handleRemove}
          />
        </aside>
      </div>

      <ConfirmDialog
        open={pendingConfirm !== null}
        title="Keep a sensitive item visible?"
        confirmLabel="Keep it visible"
        onConfirm={confirmKeep}
        onCancel={() => setPendingConfirm(null)}
      >
        <p>
          {pendingConfirm &&
            `This looks like a ${entityLabel(pendingConfirm.entity_type)}. `}
          Details like this are usually the most sensitive in a document. If you
          keep it visible, it will appear in the file you share. This choice is
          recorded.
        </p>
      </ConfirmDialog>
    </div>
  );
}
