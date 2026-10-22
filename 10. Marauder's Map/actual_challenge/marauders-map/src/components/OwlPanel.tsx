import { useEffect, useRef, useState, type FormEvent } from 'react'
import { sendOwl } from '../lib/api'

type Status = 'idle' | 'loading' | 'done' | 'error'

/**
 * The "Send an Owl" panel: give it an address and it reports back what it
 * found there. Mirrors SearchBar's structure and styling so the two read
 * as one consistent feature of the map, pinned to the opposite corner.
 */
export function OwlPanel() {
  const [open, setOpen] = useState(false)
  const [address, setAddress] = useState('')
  const [status, setStatus] = useState<Status>('idle')
  const [message, setMessage] = useState<string | null>(null)
  const [body, setBody] = useState<string | null>(null)
  const [flag, setFlag] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) requestAnimationFrame(() => inputRef.current?.focus())
  }, [open])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const a = address.trim()
    if (!a || status === 'loading') return

    setStatus('loading')
    setMessage(null)
    setBody(null)

    try {
      const data = await sendOwl(a)
      if (data.success) {
        setBody(data.body ?? null)
        setMessage(data.message ?? null)
        setStatus('done')
        setFlag(typeof data.body === 'string' && data.body.includes('kernel{'))
      } else {
        setBody(null)
        setMessage(data.message ?? 'The owl would not say what happened.')
        setStatus('error')
      }
    } catch {
      setBody(null)
      setMessage('The owl never came back. We try not to think about it.')
      setStatus('error')
    }
  }

  return (
    <div className={`parchment-panel owl-panel${open ? ' is-open' : ''}${flag ? ' is-revealed' : ''}`}>
      <button
        type="button"
        className="ink-button panel-tab"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls="owl-form"
      >
        <span>Send an Owl</span>
      </button>

      <form id="owl-form" className="panel-body" onSubmit={submit} aria-hidden={!open}>
        <p className="panel-hint">Give the owl an address, and it will fly there and report back.</p>
        <div className="panel-row">
          <input
            ref={inputRef}
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="http://somewhere-in-the-castle&hellip;"
            maxLength={500}
            autoComplete="off"
            aria-label="Address for the owl to visit"
            tabIndex={open ? 0 : -1}
          />
          <button type="submit" className="ink-button" disabled={status === 'loading'} tabIndex={open ? 0 : -1}>
            Release
          </button>
        </div>

        <div className="panel-ledger" role="status" aria-live="polite">
          {status === 'loading' && <span className="ledger-witty">An owl takes flight&hellip;</span>}
          {status !== 'loading' && message && <span className="ledger-witty">{message}</span>}
          {body && (
            <p className={`ledger-hit ledger-mono${flag ? ' ledger-flag' : ''}`}>{body}</p>
          )}
        </div>

        {flag && (
          <p className="panel-ending" role="alert">
            Mischief Managed.
          </p>
        )}
      </form>
    </div>
  )
}
