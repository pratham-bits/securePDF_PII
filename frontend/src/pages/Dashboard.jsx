import { useCallback, useEffect, useState } from "react";

import { documents } from "../api/documents.js";
import DocumentRow from "../components/DocumentRow.jsx";
import UploadZone from "../components/UploadZone.jsx";
import "./Dashboard.css";

const POLL_MS = 2000;
const ACTIVE_STATUSES = ["analyzing", "redacting"];

export default function Dashboard() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      setItems(await documents.list());
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    documents
      .list()
      .then((list) => {
        if (!cancelled) setItems(list);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // While anything is being processed, keep the list fresh.
  const hasActive = items.some((item) => ACTIVE_STATUSES.includes(item.status));
  useEffect(() => {
    if (!hasActive) return undefined;
    const timer = setInterval(refresh, POLL_MS);
    return () => clearInterval(timer);
  }, [hasActive, refresh]);

  async function handleFile(file) {
    setError("");
    setUploading(true);
    try {
      const created = await documents.upload(file);
      await documents.analyze(created.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      await refresh();
    }
  }

  async function handleAnalyze(id) {
    setError("");
    try {
      await documents.analyze(id);
    } catch (err) {
      setError(err.message);
    }
    await refresh();
  }

  async function handleDelete(id) {
    setError("");
    try {
      await documents.remove(id);
    } catch (err) {
      setError(err.message);
    }
    await refresh();
  }

  let list;
  if (loading) {
    list = <p>Loading…</p>;
  } else if (items.length === 0) {
    list = (
      <p className="dashboard__empty">
        No documents yet. Upload a PDF to begin.
      </p>
    );
  } else {
    list = items.map((item) => (
      <DocumentRow
        key={item.id}
        doc={item}
        onDelete={handleDelete}
        onAnalyze={handleAnalyze}
      />
    ));
  }

  return (
    <div className="dashboard">
      <h1>Your documents</h1>
      <p className="dashboard__lead">
        Upload a PDF, review what we find, then download the redacted copy.
        Files are deleted automatically.
      </p>

      <UploadZone onFile={handleFile} disabled={uploading} />
      {error && (
        <p className="alert alert--error" role="alert">
          {error}
        </p>
      )}

      <section className="dashboard__list" aria-label="Documents">
        {list}
      </section>
    </div>
  );
}
