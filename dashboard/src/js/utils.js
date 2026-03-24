/**
 * Utility functions
 */

export function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

export function getHue(index, total) {
  return 120 - (index / total) * 120;
}

export function getRankClass(index) {
  if (index === 0) return 'rank-1';
  if (index === 1) return 'rank-2';
  if (index === 2) return 'rank-3';
  return 'rank-other';
}

export function getExplosionClass(verdict) {
  const v = verdict.toLowerCase().replace(/\s+/g, '-');
  if (v.includes('mega')) return { item: 'explosion-mega', badge: 'badge-mega' };
  if (v.includes('viral')) return { item: 'explosion-viral', badge: 'badge-viral' };
  if (v.includes('exploding')) return { item: 'explosion-exploding', badge: 'badge-exploding' };
  return { item: 'explosion-rising', badge: 'badge-rising' };
}
