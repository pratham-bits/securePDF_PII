import { useAuth } from '../auth/useAuth.js'

export default function Dashboard() {
  const { user } = useAuth()

  return (
    <div>
      <h1>Your documents</h1>
      <p>
        Signed in as <strong>{user.email}</strong>.
      </p>
      <p>Uploading and reviewing documents arrives in the next step.</p>
    </div>
  )
}