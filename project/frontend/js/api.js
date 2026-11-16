function resolveApiBase() {
  const configuredBase = window.__APP_API_BASE__ || window.__TRAVEL_API_BASE__;
  if (configuredBase) {
    return configuredBase.replace(/\/$/, '');
  }

  const hostname = window.location.hostname;
  if (hostname === '127.0.0.1' || hostname === 'localhost') {
    return `${window.location.protocol}//${hostname}:8000`;
  }

  return window.location.origin;
}

export async function submitPlan(payload) {
  const response = await fetch(`${resolveApiBase()}/api/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to generate itinerary');
  }

  return response.json();
}

export async function getPlanStatus(sessionId) {
  const response = await fetch(`${resolveApiBase()}/api/plan/${sessionId}/status`);
  if (!response.ok) {
    throw new Error('Unable to fetch plan status');
  }
  return response.json();
}

export async function getPreferences() {
  const response = await fetch(`${resolveApiBase()}/api/preferences`);
  if (!response.ok) {
    throw new Error('Unable to load preferences');
  }
  return response.json();
}

export async function upsertPreference(payload) {
  const response = await fetch(`${resolveApiBase()}/api/preferences`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error('Unable to save preference');
  }

  return response.json();
}

export async function deletePreference(key) {
  const response = await fetch(`${resolveApiBase()}/api/preferences?key=${encodeURIComponent(key)}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error('Unable to delete preference');
  }

  return response.json();
}

export async function sendChatMessage(sessionId, message, itinerary = null) {
  const response = await fetch(`${resolveApiBase()}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message, itinerary }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to send chat message');
  }

  return response.json();
}

export async function getLogs(sessionId) {
  const response = await fetch(`${resolveApiBase()}/api/logs/${sessionId}`);
  if (!response.ok) {
    throw new Error('Unable to load session logs');
  }
  return response.json();
}
