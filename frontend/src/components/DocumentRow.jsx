import { useState } from 'react'
import { Link } from 'react-router-dom'

import { formatBytes, timeAgo, timeUntil } from '../lib/format.js'
import StatusBadge from './StatusBadge.jsx'
import './DocumentRow.css'

const ERROR_TEXT = {
  analysis_error: 'The analysis failed. You can try again.',
  interrupted: 'The server restarted while working. You can try again.',
}

export default function DocumentRow({ doc, onDelete, onAnalyze }) {
  const [confirming, setConfirming] = useState(false)

  const reviewable = doc.status === 'ready' || doc.status === 'redacted'
  const canAnalyze = doc.status === 'uploaded' || doc.status === 'failed'
  const failureText =
    doc.status === 'failed' ? ERROR_TEXT[doc.error_code] || 'Something went wrong.' : null

  return (
    <article className="doc">
      <div className="doc__main">
        <div className="doc__title">
          <strong>Document</strong>
          <span className="doc__muted">uploaded {timeAgo(doc.created_at)}</span>
          <StatusBadge status={doc.status} />
        </div>
        <p className="doc__meta">
          {doc.page_count} {doc.page_count === 1 ? 'page' : 'pages'} ·{' '}
          {formatBytes(doc.size_bytes)} · deleted automatically in {timeUntil(doc.expires_at)}
        </p>
        {failureText && <p className="doc__error">{failureText}</p>}
      </div>

      <div className="doc__actions">
        {reviewable && (
          <Link to={`/documents/${doc.id}`} className="btn btn--primary btn--small">
            {doc.status === 'redacted' ? 'Open' : 'Review'}
          </Link>
        )}
        {canAnalyze && (
          <button type="button" className="btn btn--small" onClick={() => onAnalyze(doc.id)}>
            {doc.status === 'failed' ? 'Try again' : 'Analyze'}
          </button>
        )}
        {confirming ? (
          <>
            <button
              type="button"
              className="btn btn--small btn--danger"
              onClick={() => onDelete(doc.id)}
            >
              Yes, delete
            </button>
            <button type="button" className="btn btn--small" onClick={() => setConfirming(false)}>
              Cancel
            </button>
          </>
        ) : (
          <button
            type="button"
            className="btn btn--small btn--danger"
            onClick={() => setConfirming(true)}
          >
            Delete now
          </button>
        )}
      </div>
    </article>
  )
}