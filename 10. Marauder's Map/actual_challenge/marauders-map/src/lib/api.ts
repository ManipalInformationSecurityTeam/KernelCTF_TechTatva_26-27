/**
 * Client for the public backend. Both endpoints are same-origin
 * (served by the same Flask process that serves this app in
 * production), so no base URL configuration is needed — relative
 * paths resolve correctly wherever this build is deployed.
 */

export interface AccioResult {
  name: string
  note: string
}

export interface AccioResponse {
  success: boolean
  message?: string | null
  results?: AccioResult[]
  /** True when the query surfaced something the map doesn't show by default. */
  revealed_hidden?: boolean
}

export interface OwlResponse {
  success: boolean
  message?: string | null
  status_code?: number
  body?: string
}

async function postJson<T>(path: string, payload: unknown): Promise<T> {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return (await res.json()) as T
}

export function accio(query: string): Promise<AccioResponse> {
  return postJson<AccioResponse>('/api/accio', { query })
}

export function sendOwl(address: string): Promise<OwlResponse> {
  return postJson<OwlResponse>('/api/owl', { address })
}
