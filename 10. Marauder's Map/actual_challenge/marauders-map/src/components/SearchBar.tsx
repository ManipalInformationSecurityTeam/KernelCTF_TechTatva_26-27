import { useEffect, useRef, useState, type FormEvent } from 'react'
import { accio, type AccioResult } from '../lib/api'

type Status = 'idle' | 'loading' | 'done' | 'error'

/**
 * The "Accio" panel: a small tab pinned to the map that pulls out into a
 * parchment strip holding the search field and the results ledger. Styled
 * to match .ink-button and the map's own palette rather than looking like
 * a bolted-on web form.
 */
export function SearchBar() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<Status>('idle')
  const [message, setMessage] = useState<string | null>(null)
  const [results, setResults] = useState<AccioResult[]>([])
  const [flash, setFlash] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) requestAnimationFrame(() => inputRef.current?.focus())
  }, [open])

  useEffect(() => {
    if (!flash) return
    const t = setTimeout(() => setFlash(false), 1100)
    return () => clearTimeout(t)
  }, [flash])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const q = query.trim()
    if (!q || status === 'loading') return

    setStatus('loading')
    setMessage(null)

    try {
      const data = await accio(q)
      if (data.success) {
        setResults(data.results ?? [])
        setMessage(data.message ?? null)
        setStatus('done')
        if (data.revealed_hidden) setFlash(true)
      } else {
        setResults([])
        setMessage(data.message ?? 'The map has nothing to say about that.')
        setStatus('error')
      }
    } catch {
      setResults([])
      setMessage('The ink will not settle. Something has gone wrong.')
      setStatus('error')
    }
  }

  return (
    <div className={`parchment-panel accio-panel${open ? ' is-open' : ''}${flash ? ' is-revealed' : ''}`}>
      <button
        type="button"
        className="ink-button panel-tab"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls="accio-form"
      >
        <span>Accio</span>
      </button>

      <form
        id="accio-form"
        className="panel-body"
        onSubmit={submit}
        aria-hidden={!open}
      >
        <p className="panel-hint">Speak a name, and the map will try to find them.</p>
        <div className="panel-row">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="a name…"
            maxLength={300}
            autoComplete="off"
            aria-label="Name to search for"
            tabIndex={open ? 0 : -1}
          />
          <button type="submit" className="ink-button" disabled={status === 'loading'} tabIndex={open ? 0 : -1}>
            Cast
          </button>
        </div>

        <div className="panel-ledger" role="status" aria-live="polite">
          {status === 'loading' && <span className="ledger-witty">The quill scratches&hellip;</span>}
          {status !== 'loading' && message && <span className="ledger-witty">{message}</span>}
          {results.map((r, i) => (
            <p key={`${r.name}-${i}`} className="ledger-hit">
              <strong>{r.name}</strong>
              <br />
              {r.note}
            </p>
          ))}
        </div>
      </form>
    </div>
  )
}
