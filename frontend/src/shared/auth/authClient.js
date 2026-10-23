import { getRefreshToken, setTokens, clearTokens } from './tokenStore';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || '';

export async function login(username, password) {
  const response = await fetch(`${API_BASE_URL}/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    throw new Error('Login failed');
  }

  const data = await response.json();
  setTokens(data.access, data.refresh);
  return data;
}

export async function refreshToken() {
  const refresh = getRefreshToken();
  if (!refresh) {
    clearTokens();
    throw new Error('No refresh token');
  }

  const response = await fetch(`${API_BASE_URL}/auth/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  });

  if (!response.ok) {
    clearTokens();
    throw new Error('Refresh failed');
  }

  const data = await response.json();
  setTokens(data.access, data.refresh || refresh);
  return data.access;
}

export function logout() {
  clearTokens();
}
