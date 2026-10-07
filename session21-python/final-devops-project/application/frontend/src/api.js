// The browser only talks to relative /api URLs; nginx (compose) or the Ingress (Kubernetes)
// routes them to the backend, so the frontend never needs the backend's hostname.
async function request(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join(', ') : body.detail;
    throw new Error(detail || `${res.status} ${res.statusText}`);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  categories: () => request('/categories'),
  list: (params = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
    return request(`/expenses${qs ? `?${qs}` : ''}`);
  },
  summary: () => request('/expenses/summary'),
  create: (data) => request('/expenses', { method: 'POST', body: JSON.stringify(data) }),
  remove: (id) => request(`/expenses/${id}`, { method: 'DELETE' }),
};
