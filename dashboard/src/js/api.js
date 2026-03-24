/**
 * API module - handles all API calls to FastAPI backend
 */

const API_BASE = '';

export async function getStats() {
  const response = await fetch(`${API_BASE}/api/stats`);
  return response.json();
}

export async function getTrends() {
  const response = await fetch(`${API_BASE}/api/trends`);
  return response.json();
}

export async function getSignals() {
  const response = await fetch(`${API_BASE}/api/signals`);
  return response.json();
}

export async function refreshPipeline() {
  const response = await fetch(`${API_BASE}/api/refresh`, { method: 'POST' });
  return response.json();
}

export async function loadDashboard() {
  try {
    const [stats, trends, signals] = await Promise.all([
      getStats(),
      getTrends(),
      getSignals(),
    ]);
    return { stats, trends, signals };
  } catch (error) {
    console.error('Failed to load dashboard:', error);
    throw error;
  }
}
