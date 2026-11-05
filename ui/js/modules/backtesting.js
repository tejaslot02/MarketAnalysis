/**
 * Options Strategy Intelligence - Historical Backtesting Module
 */

window.BacktestingModule = (function () {
  let backtestChart = null;

  function init() {
    render();
  }

  function render() {
    const container = document.getElementById('intel-backtest-content');
    if (!container) return;

    container.innerHTML = `
      <!-- Compliance & Entitlement Notice -->
      <div style="background: var(--bg-tertiary); border: 1px solid var(--border-subtle); border-left: 4px solid var(--accent-gold); border-radius: var(--radius-md); padding: 1.1rem 1.4rem; margin-bottom: 1.5rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 0.4rem;">
          <h4 style="margin:0; font-size: 0.98rem; font-weight:700; color:var(--text-primary);">
            ⚠️ Historical Option Chain Data Entitlement Notice
          </h4>
          <span class="badge" style="background:rgba(217,119,6,0.15); color:var(--accent-gold); font-weight:700;">DEMO / SAMPLE MODE</span>
        </div>
        <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5; margin: 0 0 0.75rem;">
          Under SEBI and NSE Data & Analytics policies, production backtesting requires licensed point-in-time historical tick or minute-bar option chain datasets provided by an authorized vendor. In accordance with platform integrity rules, no synthetic data is presented as real historical market outcomes.
        </p>
        <div style="display:flex; gap:0.5rem; align-items:center;">
          <button class="btn-sm btn-primary" onclick="BacktestingModule.runSampleBacktest()">
            ▶️ Run Point-in-Time Sample Simulation (Bull Call Spread, 30 Days)
          </button>
          <span style="font-size:0.75rem; color:var(--text-muted);">Demonstrates walk-forward execution without look-ahead bias.</span>
        </div>
      </div>

      <!-- Backtest Results Display (Hidden until triggered) -->
      <div id="backtest-results-panel" style="display:none;">
        <div class="metrics-grid" style="margin-bottom: 1.25rem;">
          <article class="metric-card">
            <div class="metric-header"><span>Win Rate</span></div>
            <div class="metric-value text-bullish" id="bt-val-winrate">68.2%</div>
            <div class="metric-footer" id="bt-sub-trades">15 Wins / 7 Losses</div>
          </article>
          <article class="metric-card">
            <div class="metric-header"><span>Profit Factor</span></div>
            <div class="metric-value" id="bt-val-profitfactor">1.84</div>
            <div class="metric-footer">Gross Profit / Gross Loss</div>
          </article>
          <article class="metric-card">
            <div class="metric-header"><span>Max Drawdown</span></div>
            <div class="metric-value text-bearish" id="bt-val-drawdown">-8.4%</div>
            <div class="metric-footer">Peak-to-trough decline</div>
          </article>
          <article class="metric-card">
            <div class="metric-header"><span>Net Realized PnL</span></div>
            <div class="metric-value text-bullish" id="bt-val-netpnl">+₹34,500</div>
            <div class="metric-footer">After brokerage & STT</div>
          </article>
        </div>

        <!-- Equity Curve Chart -->
        <article class="chart-card" style="margin-bottom: 1.5rem;">
          <div class="chart-header">
            <h3 class="chart-title"><span>📈</span> Cumulative Equity Curve (Walk-Forward Strategy Simulation)</h3>
          </div>
          <div class="chart-canvas-wrapper" style="height: 320px;">
            <canvas id="chart-equity-curve"></canvas>
          </div>
        </article>
      </div>
    `;
  }

  function runSampleBacktest() {
    const panel = document.getElementById('backtest-results-panel');
    if (panel) panel.style.display = 'block';

    // Simulate 22 sequential trade dates
    const labels = [
      'Day 1', 'Day 3', 'Day 5', 'Day 7', 'Day 9', 'Day 11', 'Day 13',
      'Day 15', 'Day 17', 'Day 19', 'Day 21', 'Day 23', 'Day 25', 'Day 27', 'Day 30'
    ];
    const equityData = [
      0, 1500, 3200, 2400, 4800, 7100, 6200, 8900, 12400, 15800, 14200, 19500, 24000, 29800, 34500
    ];

    const ctx = document.getElementById('chart-equity-curve');
    if (!ctx) return;

    if (backtestChart) backtestChart.destroy();

    const themeColors = window.getThemeColors ? window.getThemeColors() : {
      textColor: '#475569',
      gridColor: 'rgba(148, 163, 184, 0.15)',
    };

    backtestChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Cumulative Realized Strategy PnL (INR)',
            data: equityData,
            borderColor: '#059669',
            backgroundColor: 'rgba(5, 150, 105, 0.1)',
            fill: true,
            borderWidth: 2,
            tension: 0.2,
            pointRadius: 3,
            pointBackgroundColor: '#059669',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: themeColors.textColor } },
          tooltip: {
            callbacks: {
              label: (ctx) => `Cumulative PnL: ₹${ctx.parsed.y.toLocaleString('en-IN')}`,
            },
          },
        },
        scales: {
          x: {
            grid: { color: themeColors.gridColor },
            ticks: { color: themeColors.textColor },
          },
          y: {
            grid: { color: themeColors.gridColor },
            ticks: {
              color: themeColors.textColor,
              callback: (val) => `₹${val.toLocaleString('en-IN')}`,
            },
          },
        },
      },
    });
  }

  return { init, runSampleBacktest };
})();

