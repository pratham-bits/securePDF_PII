import { Link, useParams } from 'react-router-dom'

export default function Review() {
  const { id } = useParams()

  return (
    <div>
      <h1>Review</h1>
      <p>
        The review screen for document <code>{id.slice(0, 8)}</code> arrives in the next step.
      </p>
      <Link to="/dashboard" className="btn">
        Back to documents
      </Link>
    </div>
  )
}