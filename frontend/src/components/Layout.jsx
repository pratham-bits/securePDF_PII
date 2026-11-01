import { Link, Outlet } from 'react-router-dom'

import './Layout.css'

export default function Layout() {
  return (
    <div className="layout">
      <header className="layout__header">
        <div className="layout__inner">
          <Link to="/" className="brand" aria-label="SecurePDF home">
            <span className="brand__mark" aria-hidden="true" />
            SecurePDF
          </Link>
          <nav className="layout__nav">
            <Link to="/">Home</Link>
          </nav>
        </div>
      </header>
      <main className="layout__main">
        <Outlet />
      </main>
      <footer className="layout__footer">
        <div className="layout__inner">
          An assistive tool: always review the result before sharing a document.
        </div>
      </footer>
    </div>
  )
}