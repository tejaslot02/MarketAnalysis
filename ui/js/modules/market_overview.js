/**
 * Options Strategy Intelligence - Market Overview Module
 */

window.MarketOverviewModule = (function () {
  async function load(symbol = 'NIFTY') {
    const container = document.getElementById('intel-overview-content');
    if (!container) return;

    try {
      container.innerHTML = '<div style="text-align:center; padding: 2.5rem; color: var(--text-muted);">Analyzing market regime & volatility skew...</div>';
      const res = await fetch(`/api/options/market-summary?symbol=${encodeURIComponent(symbol)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      render(data);
    } catch (e) {
      container.innerHTML = `<div style="text-align:center; padding: 2rem; color: var(--bearish);">Failed to load Market Overview: ${e.message}</div>`;
    }
  }

  function render(data) {
    const container = document.getElementById('intel-overview-content');
    if (!container) return;

    const ind = data.indicators || {};
    const reg = data.regime || {};
    const conc = data.concentrations || [];

    const regimeColorMap = {
      BULLISH: 'var(--bullish)',
      BEARISH: 'var(--bearish)',
      NEUTRAL: 'var(--accent-gold)',
      VOLATILITY: 'var(--accent-blue)',
    };
    const regColor = regimeColorMap[reg.directional_bias] || 'var(--accent-blue)';

    let reasonsHtml = (reg.reasons || [])
      .map((r) => `<li style="margin-bottom: 0.35rem; color: var(--text-secondary); font-size: 0.85rem;">• ${r}</li>`)
      .join('');

    let concRows = conc
      .map(
        (c) => `
        <tr>
          <td style="text-align:left; font-weight:700;">${c.strike.toLocaleString('en-IN')}</td>
          <td>${c.total_oi.toLocaleString('en-IN')}</td>
          <td><span class="badge" style="background:rgba(56,189,248,0.15); color:var(--accent-blue);">${c.oi_share}%</span></td>
          <td>${c.total_vol.toLocaleString('en-IN')}</td>
          <td><span class="badge" style="background:rgba(251,191,36,0.15); color:var(--accent-gold);">${c.vol_share}%</span></td>
        </tr>`
      )
      .join('');

    container.innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.25rem; margin-bottom: 1.5rem;">
        <!-- Regime Card -->
        <article class="metric-card" style="border-left: 4px solid ${regColor};">
          <div class="metric-header">
            <span>Market Structural Regime</span>
            <span class="badge" style="background:${regColor}; color:#fff; font-weight:700;">${reg.regime || 'UNKNOWN'}</span>
          </div>
          <div style="font-size: 1.15rem; font-weight: 700; color: var(--text-primary); margin: 0.5rem 0 0.3rem;">
            ${reg.summary || ''}
          </div>
          <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.75rem;">
            Confidence: <strong style="color:var(--text-primary);">${reg.confidence_pct || 0}%</strong> | Favored Strategies: <strong style="color:var(--text-primary);">${(reg.favored_categories || []).join(', ')}</strong>
          </div>
          <ul style="list-style:none; padding:0; margin:0;">
            ${reasonsHtml}
          </ul>
        </article>

        <!-- Positioning Summary Card -->
        <article class="metric-card">
          <div class="metric-header">
            <span>Option-Chain Positioning Core</span>
            <span class="metric-tooltip" title="Quantitative indicator readings">ℹ</span>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; margin-top: 0.5rem;">
            <div>
              <div style="font-size:0.75rem; color:var(--text-muted);">ATM Strike</div>
              <div style="font-size:1.15rem; font-weight:700; font-family:'JetBrains Mono';">${(ind.atm_strike || 0).toLocaleString('en-IN')}</div>
            </div>
            <div>
              <div style="font-size:0.75rem; color:var(--text-muted);">Max Pain Strike</div>
              <div style="font-size:1.15rem; font-weight:700; font-family:'JetBrains Mono'; color:var(--accent-gold);">${(ind.max_pain_strike || 0).toLocaleString('en-IN')}</div>
            </div>
            <div>
              <div style="font-size:0.75rem; color:var(--text-muted);">PCR (Open Interest)</div>
              <div style="font-size:1.15rem; font-weight:700; font-family:'JetBrains Mono';">${(ind.pcr_oi || 0).toFixed(2)}</div>
            </div>
            <div>
              <div style="font-size:0.75rem; color:var(--text-muted);">PCR (Volume)</div>
              <div style="font-size:1.15rem; font-weight:700; font-family:'JetBrains Mono';">${(ind.pcr_volume || 0).toFixed(2)}</div>
            </div>
            <div>
              <div style="font-size:0.75rem; color:var(--text-muted);">ATM Implied Volatility</div>
              <div style="font-size:1.15rem; font-weight:700; font-family:'JetBrains Mono'; color:var(--accent-blue);">${(ind.atm_iv || 0).toFixed(1)}%</div>
            </div>
            <div>
              <div style="font-size:0.75rem; color:var(--text-muted);">Liquidity Score</div>
              <div style="font-size:1.15rem; font-weight:700; font-family:'JetBrains Mono'; color:var(--bullish);">${ind.chain_liquidity_score || 0}/100</div>
            </div>
          </div>
        </article>
      </div>

      <!-- Strike Concentrations Heatmap -->
      <div class="table-card" style="margin-top: 1rem;">
        <div style="padding: 1rem 1.25rem; border-bottom: 1px solid var(--border-subtle); display:flex; justify-content:space-between; align-items:center;">
          <h3 style="font-size:0.95rem; font-weight:700; margin:0;">Strike-wise Interest & Volume Concentration</h3>
          <span style="font-size:0.78rem; color:var(--text-muted);">Top active liquidity hubs</span>
        </div>
        <div class="table-responsive">
          <table class="option-table" style="text-align:right;">
            <thead>
              <tr>
                <th style="text-align:left;">Strike Price</th>
                <th>Total Open Interest</th>
                <th>OI Share</th>
                <th>Total Traded Volume</th>
                <th>Volume Share</th>
              </tr>
            </thead>
            <tbody>
              ${concRows || '<tr><td colspan="5" style="text-align:center;">No concentrations available.</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  return { load, render };
})();

