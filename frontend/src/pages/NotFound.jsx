import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div>
      <h1>Page not found</h1>
      <p>That page doesn't exist.</p>
      <Link to="/" className="btn">
        Back to home
      </Link>
    </div>
  )
}