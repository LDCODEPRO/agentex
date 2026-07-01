const BASE = '/api';

async function req(path, opts = {}) {
  const res = await fetch(BASE + path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (res.status === 401) {
    const err = new Error('unauthenticated');
    err.status = 401;
    throw err;
  }
  if (!res.ok) {
    const err = new Error('request failed: ' + res.status);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const api = {
  me: () => req('/me'),
  login: (password) => req('/login', { method: 'POST', body: JSON.stringify({ password }) }),
  logout: () => req('/logout', { method: 'POST' }),

  overview: () => req('/overview'),
  activity: () => req('/activity'),
  systemHealth: () => req('/health/system'),
  chat: (message) => req('/chat', { method: 'POST', body: JSON.stringify({ message }) }),
  missions: (status) => req('/missions?status=' + encodeURIComponent(status || 'all')),
  queue: () => req('/queue'),
  brains: () => req('/brains'),
  memoryTabs: () => req('/memory/tabs'),
  memory: (tab) => req('/memory?tab=' + encodeURIComponent(tab)),
  logs: (level) => req('/logs?level=' + encodeURIComponent(level || 'ALL')),
  securityBlocked: () => req('/security/blocked'),
  finance: () => req('/finance'),
  settings: () => req('/settings'),
};
