/** Shared API wrapper with cookie credentials and auth-expiry handling. */
export async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    credentials: 'same-origin',
    headers: {
      ...(options.headers || {})
    }
  })

  if (response.status === 401) {
    window.dispatchEvent(new CustomEvent('auth:unauthorized'))
  }
  return response
}

