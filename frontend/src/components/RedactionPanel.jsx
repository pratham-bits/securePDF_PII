import "./RedactionPanel.css";

const FAILURE_TEXT = {
  verification_failed:
    "We could not verify that the sensitive content was removed, so no file was produced. " +
    "Try again. If it keeps failing, add a box over the affected area.",
  redaction_error: "Something went wrong while redacting. Please try again.",
  interrupted: "The server restarted during redaction. Please try again.",
};

export default function RedactionPanel({
  doc,
  findings,
  starting,
  downloading,
  onRedact,
  onDownload,
}) {
  const toRedact = findings.filter(
    (finding) => finding.decision === "redact",
  ).length;
  const kept = findings.length - toRedact;

  if (doc.status === "redacting") {
    return (
      <section className="action" aria-live="polite">
        <div>
          <p className="action__title">Redacting and verifying…</p>
          <p className="action__text">
            This can take a minute for scanned documents. You can leave this
            page open.
          </p>
        </div>
      </section>
    );
  }

  if (doc.status === "redacted") {
    return (
      <section className="action action--done" aria-live="polite">
        <div>
          <p className="action__title">Your redacted file is ready</p>
          <p className="action__text">
            We re-checked the file and found no readable content under the
            redacted areas. Open it and look before you share it. If you change
            anything here, redact again.
          </p>
        </div>
        <button
          type="button"
          className="btn btn--primary"
          disabled={downloading}
          onClick={onDownload}
        >
          {downloading ? "Preparing…" : "Download redacted PDF"}
        </button>
      </section>
    );
  }

  const failureText = doc.error_code ? FAILURE_TEXT[doc.error_code] : null;

  return (
    <section className="action" aria-live="polite">
      <div>
        <p className="action__title">
          {toRedact} {toRedact === 1 ? "item" : "items"} to redact · {kept} kept
          visible
        </p>
        <p className="action__text">
          {toRedact === 0
            ? "Nothing is selected for redaction, so the copy will only have its hidden metadata removed."
            : "When you are happy with the review, create the redacted copy."}
        </p>
        {failureText && <p className="action__error">{failureText}</p>}
      </div>
      <button
        type="button"
        className="btn btn--primary"
        disabled={starting}
        onClick={onRedact}
      >
        {starting ? "Starting…" : "Redact document"}
      </button>
    </section>
  );
}
