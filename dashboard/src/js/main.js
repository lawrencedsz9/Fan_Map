/**
 * Main entry point - orchestrates the dashboard
 */

import { loadDashboard, refreshPipeline } from './api.js';
import { renderStats, renderRankings, renderExplosions, renderSignals } from './render.js';

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', initDashboard);

async function initDashboard() {
  // Load initial data
  await updateDashboard();

  // Set up event listeners
  const refreshBtn = document.getElementById('refresh-btn');
  refreshBtn.addEventListener('click', handleRefresh);
}

async function updateDashboard() {
  try {
    const { stats, trends, signals } = await loadDashboard();
    
    renderStats(stats);
    renderRankings(stats.rankings || []);
    renderExplosions(trends.explosions || [], trends);
    renderSignals(signals);
  } catch (error) {
    console.error('Failed to update dashboard:', error);
  }
}

async function handleRefresh() {
  const btn = document.getElementById('refresh-btn');
  btn.disabled = true;
  btn.textContent = 'Refreshing...';

  try {
    await refreshPipeline();
    await updateDashboard();
  } catch (error) {
    console.error('Refresh failed:', error);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Refresh Data';
  }
}

