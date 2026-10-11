const base = import.meta.env.VITE_API_URL || '/api';

export async function api(path, options = {}) {
  const response = await fetch(`${base}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Unable to complete the request. Please try again.');
  }
  return data;
}
