function normalizeApiBase(raw) {
  const trimmed = (raw || 'http://localhost:8000').trim().replace(/\/+$/, '')
  if (/^https?:\/\//i.test(trimmed)) return trimmed
  const isLocal =
    /^localhost\b/i.test(trimmed) ||
    /^127\.\d+\.\d+\.\d+/.test(trimmed) ||
    /^\[::1\]/.test(trimmed)
  return `${isLocal ? 'http' : 'https'}://${trimmed}`
}

const API_BASE_URL = normalizeApiBase(import.meta.env.VITE_API_URL)

export function apiUrl(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${normalizedPath}`
}
