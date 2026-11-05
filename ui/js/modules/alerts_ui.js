/**
 * Options Strategy Intelligence - Alerts & Notifications Module
 */

window.AlertsModule = (function () {
  let activeAlertRules = [
    { id: 1, type: 'PCR_THRESHOLD', label: 'PCR (OI) > 1.35 (Bullish Extreme)', threshold: 1.35, is_active: true },
    { id: 2, type: 'PCR_THRESHOLD', label: 'PCR (OI) < 0.70 (Bearish Supply)', threshold: 0.70, is_active: true },
    { id: 3, type: 'IV_SPIKE', label: 'ATM IV Spike > 25.0% (Event Risk)', threshold: 25.0, is_active: true },
    { id: 4, type: 'STRATEGY_QUALIFIED', label: 'Strategy Quality Score >= 85/100', threshold: 85.0, is_active: true },
  ];

  let recentTriggers = [
    { time: '12:25:04', symbol: 'NIFTY', message: 'Bull Call Spread achieved Quality Score of 88.0/100', severity: 'success' },
    { time: '11:45:12', symbol: 'BANKNIFTY', message: 'PCR (OI) crossed 1.25 pivot support', severity: 'info' },
  ];

  function init() {
    render();
  }

  function render() {
    const container = document.getElementById('intel-alerts-content');
    if (!container) return;

    let rulesHtml = activeAlertRules
      .map(
        (r) => `
        <div style="display:flex; justify-content:space-between; align-items:center; padding:0.65rem 0.85rem; background:var(--bg-tertiary); border:1px solid var(--border-subtle); border-radius:var(--radius-sm); margin-bottom:0.5rem;">
          <div>
            <strong style="font-size:0.85rem; color:var(--text-primary);">${r.label}</strong>
            <div style="font-size:0.75rem; color:var(--text-muted);">Trigger Threshold: ${r.threshold}</div>
          </div>
          <div>
            <span class="badge ${r.is_active ? 'badge-bullish' : 'badge-neutral'}">${r.is_active ? 'ACTIVE' : 'MUTED'}</span>
          </div>
        </div>`
      )
      .join('');

    let triggersHtml = recentTriggers
      .map(
        (t) => `
        <div style="display:flex; justify-content:space-between; align-items:center; padding:0.6rem 0.85rem; border-bottom:1px solid var(--border-subtle); font-size:0.82rem;">
          <div>
            <span style="font-family:'JetBrains Mono'; color:var(--text-muted); margin-right:0.5rem;">${t.time}</span>
            <strong style="color:var(--text-primary); margin-right:0.4rem;">${t.symbol}:</strong>
            <span style="color:var(--text-secondary);">${t.message}</span>
          </div>
          <span class="badge badge-${t.severity}">${t.severity.toUpperCase()}</span>
        </div>`
      )
      .join('');

    container.innerHTML = `
      <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.5rem;">
        <!-- Configured Rules -->
        <article class="metric-card">
          <div class="metric-header">
            <span>Configured Real-Time Alert Triggers</span>
            <span class="metric-tooltip" title="Autonomous event monitors">ℹ</span>
          </div>
          <div style="margin-top:0.75rem;">
            ${rulesHtml}
          </div>
        </article>

        <!-- Trigger Logs -->
        <article class="metric-card">
          <div class="metric-header">
            <span>Recent Event Notifications Stream</span>
            <span class="badge badge-info">LIVE STREAM</span>
          </div>
          <div style="margin-top:0.75rem;">
            ${triggersHtml || '<div style="color:var(--text-muted); text-align:center; padding:1.5rem;">No alerts triggered yet.</div>'}
          </div>
        </article>
      </div>
    `;
  }

  return { init };
})();

