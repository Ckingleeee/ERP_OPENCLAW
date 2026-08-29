import { apiFetch } from './http.js'

export async function login(username, password) {
  const response = await apiFetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || '登录失败')
  }
  return data.user
}

export async function getCurrentUser() {
  const response = await apiFetch('/api/auth/me')
  if (response.status === 401) return null
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || '无法获取当前用户')
  }
  return data.user
}

export async function logout() {
  const response = await apiFetch('/api/auth/logout', { method: 'POST' })
  if (!response.ok) {
    throw new Error('退出登录失败')
  }
}

