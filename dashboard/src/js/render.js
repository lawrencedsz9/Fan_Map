/**
 * Rendering module - all DOM updates
 */

import { escapeHtml, getHue, getRankClass, getExplosionClass } from './utils.js';

export function renderStats(stats) {
  const types = stats.node_types || {};
  const statsRow = document.getElementById('stats-row');
  
  statsRow.innerHTML = `
    <div class="stat-card">
      <div class="stat-value" style="color: var(--accent)">${stats.anime_count || 0}</div>
      <div class="stat-label">Anime Tracked</div>
    </div>
    <div class="stat-card">
      <div class="stat-value" style="color: var(--accent2)">${stats.total_nodes || 0}</div>
      <div class="stat-label">Graph Nodes</div>
    </div>
    <div class="stat-card">
      <div class="stat-value" style="color: var(--accent3)">${stats.total_edges || 0}</div>
      <div class="stat-label">Connections</div>
    </div>
    <div class="stat-card">
      <div class="stat-value" style="color: var(--accent4)">${types.Character || 0}</div>
      <div class="stat-label">Characters Found</div>
    </div>
  `;
}

export function renderRankings(rankings) {
  const rankingsEl = document.getElementById('rankings');
  
  if (!rankings || !rankings.length) {
    rankingsEl.innerHTML = '<div class="loading">No data yet</div>';
    return;
  }

  const maxScore = Math.max(...rankings.map(r => r.attention_score || 0));

  rankingsEl.innerHTML = rankings.map((r, i) => {
    const pct = maxScore > 0 ? ((r.attention_score || 0) / maxScore) * 100 : 0;
    const hue = getHue(i, rankings.length);
    const rankClass = getRankClass(i);
    const rank = i + 1;

    return `
      <div class="ranking-item">
        <div class="rank-badge ${rankClass}">${rank}</div>
        <div class="rank-info">
          <div class="rank-name">${r.anime || 'Unknown'}</div>
          <div class="rank-meta">
            Reddit: ${r.reddit_mentions || 0} &middot;
            YouTube: ${r.youtube_mentions || 0} &middot;
            Trends: ${r.google_trends_score || 0}
          </div>
        </div>
        <div class="attention-bar-wrap">
          <div class="attention-bar" style="width:${pct}%; background: hsl(${hue}, 70%, 55%)"></div>
        </div>
        <div class="score-value" style="color: hsl(${hue}, 70%, 55%)">${((r.attention_score || 0) * 100).toFixed(0)}</div>
      </div>
    `;
  }).join('');
}

export function renderExplosions(explosions, trends) {
  const explosionsEl = document.getElementById('explosions');
  
  if (!explosions.length) {
    const tracked = trends.topics_tracked || 0;
    explosionsEl.innerHTML = `
      <div style="text-align:center; padding: 40px; color: var(--muted)">
        <div style="font-weight: 600; margin-bottom: 4px;">No explosions detected (yet)</div>
        <div style="font-size: 13px;">Monitoring ${tracked} topics &mdash; run more collection cycles to build baseline data</div>
      </div>
    `;
    return;
  }

  explosionsEl.innerHTML = explosions.map(e => {
    const classes = getExplosionClass(e.verdict);

    return `
      <div class="explosion-item ${classes.item}">
        <div class="explosion-header">
          <span class="explosion-topic">${e.topic}</span>
          <span class="explosion-badge ${classes.badge}">${e.verdict}</span>
        </div>
        <div class="explosion-stats">
          <span>${e.explosion_ratio}x baseline</span>
          <span>Current: ${e.current_mentions}</span>
          <span>Avg: ${e.baseline_average}</span>
        </div>
      </div>
    `;
  }).join('');
}

export function renderSignals(signals) {
  const signalsEl = document.getElementById('signals');
  
  if (!signals || !signals.length) {
    signalsEl.innerHTML = '<div class="loading">No signals collected</div>';
    return;
  }

  signalsEl.innerHTML = signals.slice(0, 40).map(s => {
    const src = s.source || 'unknown';
    const srcClass = `source-${src}`;
    const title = s.title || s.topic || 'Unknown';
    const topics = (s.matched_topics || []).join(', ');

    return `
      <div class="signal-item">
        <span class="signal-source ${srcClass}">${src}</span>
        <div class="signal-title">${escapeHtml(title)}</div>
        ${topics ? `<div class="signal-topics">${escapeHtml(topics)}</div>` : ''}
      </div>
    `;
  }).join('');
}
