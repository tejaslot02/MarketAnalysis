/**
 * Options Strategy Intelligence - Strategy Scanner Module
 */

window.StrategyScannerModule = (function () {
  let activeCategory = 'ALL';
  let cachedStrategies = [];

  async function load(symbol = 'NIFTY') {
    const grid = document.getElementById('strategy-cards-grid');
    if (!grid) return;

    grid.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding: 3rem; color: var(--text-muted);">Evaluating 16 classical strategy algorithms across option chain...</div>';

    try {
      const res = await fetch(`/api/options/strategies?symbol=${encodeURIComponent(symbol)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      cachedStrategies = data.strategies || [];
      render();
    } catch (e) {
      grid.innerHTML = `<div style="grid-column: 1/-1; text-align:center; padding: 2rem; color: var(--bearish);">Failed to evaluate strategies: ${e.message}</div>`;
    }
  }

  function setCategory(cat) {
    activeCategory = cat.toUpperCase();
    document.querySelectorAll('.cat-pill').forEach((btn) => {
      if (btn.dataset.category.toUpperCase() === activeCategory) btn.classList.add('active');
      else btn.classList.remove('active');
    });
    render();
  }

  function render() {
    const grid = document.getElementById('strategy-cards-grid');
    if (!grid) return;

    let list = cachedStrategies;
    if (activeCategory !== 'ALL') {
      list = list.filter((s) => s.category.toUpperCase() === activeCategory);
    }

    if (list.length === 0) {
      grid.innerHTML = `<div style="grid-column: 1/-1; text-align:center; padding: 3rem; color: var(--text-muted);">No strategies matching category "${activeCategory}".</div>`;
      return;
    }

    grid.innerHTML = list.map((s, idx) => buildCardHtml(s, idx)).join('');
  }

  function buildCardHtml(s, idx) {
    const isCredit = s.net_debit_credit < 0;
    const debitCreditLabel = isCredit ? 'Net Credit' : 'Net Debit';
    const debitCreditVal = Math.abs(s.net_debit_credit).toLocaleString('en-IN', { maximumFractionDigits: 1 });
    const debitCreditColor = isCredit ? 'var(--bullish)' : 'var(--accent-gold)';

    const maxProfitStr = s.max_profit !== null ? `₹${s.max_profit.toLocaleString('en-IN')}` : 'Unlimited 🚀';
    const maxLossStr = s.max_loss !== null ? `₹${s.max_loss.toLocaleString('en-IN')}` : 'Unlimited ⚠️';
    const rrStr = s.reward_to_risk !== null ? `1 : ${s.reward_to_risk}` : (s.max_profit === null ? 'High' : 'N/A');

    const statusBadgeClass = s.status === 'QUALIFIED' ? 'status-qualified' : (s.status === 'WATCHLIST' ? 'status-watchlist' : 'status-rejected');

    const legsHtml = (s.legs || [])
      .map(
        (l) => `
        <div style="display:flex; justify-content:space-between; font-size:0.8rem; padding: 0.2rem 0; border-bottom: 1px dashed var(--border-subtle);">
          <span style="font-weight:600; color:${l.action === 'BUY' ? 'var(--accent-blue)' : 'var(--bearish)'};">
            ${l.action} ${l.strike_price} ${l.option_type}
          </span>
          <span style="font-family:'JetBrains Mono'; color:var(--text-secondary);">
            ₹${l.entry_price.toFixed(2)} (${l.quantity} Qty)
          </span>
        </div>`
      )
      .join('');

    return `
      <article class="strategy-card">
        <div class="strategy-card-header">
          <div>
            <div style="display:flex; align-items:center; gap:0.4rem; margin-bottom:0.25rem;">
              <span class="badge badge-category badge-${s.category.toLowerCase()}">${s.category}</span>
              <span class="badge ${statusBadgeClass}">${s.status}</span>
            </div>
            <h4 style="font-size:1.05rem; font-weight:700; color:var(--text-primary); margin:0;">${s.name}</h4>
            <div style="font-size:0.75rem; color:var(--text-muted);">${s.directional_bias}</div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:1.25rem; font-weight:800; font-family:'JetBrains Mono'; color:var(--accent-blue);">
              ${s.confidence_score}<span style="font-size:0.75rem; color:var(--text-muted);">/100</span>
            </div>
            <div style="font-size:0.7rem; color:var(--text-muted);">Quality Score</div>
          </div>
        </div>

        <div class="strategy-stats-grid">
          <div>
            <span class="stat-lbl">${debitCreditLabel}</span>
            <span class="stat-val" style="color:${debitCreditColor};">₹${debitCreditVal}</span>
          </div>
          <div>
            <span class="stat-lbl">Max Profit</span>
            <span class="stat-val text-bullish">${maxProfitStr}</span>
          </div>
          <div>
            <span class="stat-lbl">Max Risk / Loss</span>
            <span class="stat-val text-bearish">${maxLossStr}</span>
          </div>
          <div>
            <span class="stat-lbl">Reward / Risk</span>
            <span class="stat-val">${rrStr}</span>
          </div>
          <div>
            <span class="stat-lbl">Est. Margin</span>
            <span class="stat-val">₹${s.estimated_margin.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
          </div>
          <div>
            <span class="stat-lbl">Portfolio Delta</span>
            <span class="stat-val font-mono">${s.portfolio_delta.toFixed(2)}</span>
          </div>
        </div>

        <div style="margin: 0.75rem 0;">
          <div style="font-size:0.72rem; text-transform:uppercase; color:var(--text-muted); font-weight:700; margin-bottom:0.3rem;">Strategy Legs</div>
          ${legsHtml}
        </div>

        <div class="strategy-actions">
          <button class="btn-sm btn-outline" onclick="StrategyScannerModule.inspectRules(${idx})">
            ℹ️ Inspect Rules
          </button>
          <button class="btn-sm btn-primary" onclick="StrategyScannerModule.sendToSimulator(${idx})">
            📊 Send to Simulator
          </button>
        </div>
      </article>
    `;
  }

  function inspectRules(idx) {
    const s = cachedStrategies[idx];
    if (!s) return;

    const modal = document.getElementById('rule-inspect-modal');
    const title = document.getElementById('modal-strategy-title');
    const body = document.getElementById('modal-strategy-body');

    if (!modal || !title || !body) return;

    title.textContent = `${s.name} (${s.category}) — Evaluation Audit`;

    let passedHtml = (s.passed_rules || []).map((r) => `<li style="color:var(--bullish); margin-bottom:0.4rem;">✅ ${r}</li>`).join('');
    let failedHtml = (s.failed_rules || []).map((r) => `<li style="color:var(--bearish); margin-bottom:0.4rem;">⚠️ ${r}</li>`).join('');
    let invalHtml = (s.invalidations || []).map((r) => `<li style="color:var(--text-secondary); margin-bottom:0.4rem;">⛔ ${r}</li>`).join('');

    body.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; background:var(--bg-tertiary); padding:0.75rem 1rem; border-radius:var(--radius-sm); margin-bottom:1rem;">
        <div>
          <span style="font-size:0.8rem; color:var(--text-muted);">Overall Confidence Score:</span>
          <strong style="font-size:1.2rem; color:var(--accent-blue); margin-left:0.5rem;">${s.confidence_score}/100</strong>
        </div>
        <div>
          <span style="font-size:0.8rem; color:var(--text-muted);">Evaluation Status:</span>
          <strong style="margin-left:0.5rem;">${s.status}</strong>
        </div>
      </div>

      <h5 style="margin: 0.5rem 0; font-size:0.88rem; font-weight:700;">Passed Criteria & Quantitative Tailwinds</h5>
      <ul style="list-style:none; padding:0; margin:0 0 1rem; font-size:0.84rem;">
        ${passedHtml || '<li style="color:var(--text-muted);">No criteria passed.</li>'}
      </ul>

      <h5 style="margin: 0.5rem 0; font-size:0.88rem; font-weight:700;">Failed Hurdle Rules & Risk Friction</h5>
      <ul style="list-style:none; padding:0; margin:0 0 1rem; font-size:0.84rem;">
        ${failedHtml || '<li style="color:var(--text-muted);">None (All evaluated rules passed cleanly).</li>'}
      </ul>

      <h5 style="margin: 0.5rem 0; font-size:0.88rem; font-weight:700;">Invalidation & Exit Conditions</h5>
      <ul style="list-style:none; padding:0; margin:0; font-size:0.84rem;">
        ${invalHtml || '<li style="color:var(--text-muted);">None specified.</li>'}
      </ul>
    `;

    modal.classList.add('active');
  }

  function sendToSimulator(idx) {
    const s = cachedStrategies[idx];
    if (!s) return;

    if (window.PayoffSimulatorModule) {
      window.PayoffSimulatorModule.loadFromStrategy(s);
    }

    // Switch to simulator tab
    const simTabBtn = document.getElementById('intel-tab-simulator-btn');
    if (simTabBtn) simTabBtn.click();
  }

  return { load, setCategory, inspectRules, sendToSimulator };
})();

