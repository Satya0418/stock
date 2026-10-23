import { getAccessToken } from '../auth/tokenStore';
import { refreshToken } from '../auth/authClient';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || '';

function buildUrl(path) {
  if (path.startsWith('http')) {
    return path;
  }
  return `${API_BASE_URL}${path}`;
}

async function parseJson(response) {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch (error) {
    return text;
  }
}

export async function fetchJson(path, options = {}, retryOnAuth = true) {
  const { timeout = 15000, ...fetchOptions } = options;
  const controller = new AbortController();
  const headers = {
    'Content-Type': 'application/json',
    ...(fetchOptions.headers || {}),
  };

  const accessToken = getAccessToken();
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }

  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(buildUrl(path), {
      ...fetchOptions,
      headers,
      signal: controller.signal,
    });

    if (response.status === 401 && retryOnAuth) {
      await refreshToken();
      return fetchJson(path, options, false);
    }

    if (!response.ok) {
      const data = await parseJson(response);
      const message = typeof data === 'string' ? data : data?.error || 'Request failed';
      throw new Error(message);
    }

    return parseJson(response);
  } finally {
    clearTimeout(timer);
  }
}
