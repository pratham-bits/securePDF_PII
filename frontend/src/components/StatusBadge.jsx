import './StatusBadge.css'

const LABELS = {
  uploaded: 'Uploaded',
  analyzing: 'Analyzing…',
  ready: 'Ready to review',
  redacting: 'Redacting…',
  redacted: 'Redacted',
  failed: 'Failed',
}

export default function StatusBadge({ status }) {
  return <span className={`badge badge--${status}`}>{LABELS[status] || status}</span>
}