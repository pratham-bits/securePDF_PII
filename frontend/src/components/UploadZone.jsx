import { useRef, useState } from 'react'

import { useConfig } from '../lib/useConfig.js'
import './UploadZone.css'

export default function UploadZone({ onFile, disabled }) {
  // Mirrors the server limits; the server is the real authority.
  const { max_upload_mb: MAX_MB, max_pages: maxPages } = useConfig()
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')

  function accept(file) {
    if (!file) return
    const looksLikePdf =
      file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
    if (!looksLikePdf) {
      setError('Please choose a PDF file.')
      return
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(`The file is larger than ${MAX_MB} MB.`)
      return
    }
    setError('')
    onFile(file)
  }

  function handleDrop(event) {
    event.preventDefault()
    setDragging(false)
    if (!disabled) accept(event.dataTransfer.files[0])
  }

  function handleChange(event) {
    accept(event.target.files[0])
    event.target.value = '' // lets the same file be chosen again
  }

  const classes = ['upload']
  if (dragging) classes.push('upload--active')
  if (disabled) classes.push('upload--disabled')

  return (
    <div>
      <div
        className={classes.join(' ')}
        onDragOver={(event) => {
          event.preventDefault()
          if (!disabled) setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <p className="upload__title">Drag a PDF here</p>
        <p className="upload__hint">or</p>
        <button
          type="button"
          className="btn btn--primary"
          disabled={disabled}
          onClick={() => inputRef.current.click()}
        >
          {disabled ? 'Uploading…' : 'Choose a file'}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          hidden
          onChange={handleChange}
        />
        <p className="upload__hint">
          PDF only, up to {MAX_MB} MB and {maxPages} pages. Scanned PDFs are supported.
        </p>
      </div>
      {error && (
        <p className="alert alert--error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}