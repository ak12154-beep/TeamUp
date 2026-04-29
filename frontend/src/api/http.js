const BASE_URL = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')
export const COOKIE_SESSION_TOKEN = '__cookie_session__'

export function withQuery(path, params = {}) {
 const searchParams = new URLSearchParams()

 Object.entries(params).forEach(([key, value]) => {
  if (value !== undefined && value !== null && value !== '') {
   searchParams.set(key, String(value))
  }
 })

 const query = searchParams.toString()
 return query ? `${path}?${query}` : path
}

export async function http(path, { method = 'GET', body, token } = {}) {
 const shouldSendBearer = token && token !== COOKIE_SESSION_TOKEN
 const headers = {
  Accept: 'application/json',
  ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
  ...(shouldSendBearer ? { Authorization: `Bearer ${token}` } : {}),
 }

 const res = await fetch(`${BASE_URL}${path}`, {
  method,
  credentials: 'include',
  headers,
  body: body ? JSON.stringify(body) : undefined,
 })

 if (!res.ok) {
  let detail = 'Request failed'
  const retryAfterHeader = res.headers.get('Retry-After')
  const retryAfter = retryAfterHeader ? Number.parseInt(retryAfterHeader, 10) : null
  try {
   const data = await res.json()
   if (typeof data.detail === 'string') {
    detail = data.detail
   } else if (Array.isArray(data.detail)) {
    detail = data.detail.map((e) => e.msg || e.message || JSON.stringify(e)).join(', ')
   } else if (data.detail) {
    detail = JSON.stringify(data.detail)
   }
  } catch {
   // ignore parse errors
  }
  const error = new Error(detail)
  error.status = res.status
  error.retryAfter = Number.isFinite(retryAfter) ? retryAfter : null
  throw error
 }

 if (res.status === 204) return null
 return res.json()
}
