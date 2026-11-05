/**
 * Options Strategy Intelligence - Payoff Simulator & Scenario Analysis Module
 */

window.PayoffSimulatorModule = (function () {
  let activeLegs = [];
  let currentSpot = 24250.0;
  let activeSymbol = 'NIFTY';
  let activeLotSize = 25;
  let payoffChart = null;

  function init() {
    // Default initial strategy: Bull Call Spread on NIFTY
    if (activeLegs.length === 0) {
      activeLegs = [
        { action: 'BUY', option_type: 'CE', strike: 24250.0, quantity: 25, entry_price: 120.0, iv: 16.0 },
        { action: 'SELL', option_type: 'CE', strike: 24350.0, quantity: 25, entry_price: 60.0, iv: 15.5 },
      ];
    }
    renderLegsTable();
    recalculate();
  }

  function loadFromStrategy(strat) {
    activeSymbol = strat.symbol || 'NIFTY';
    currentSpot = strat.underlying_value || 24250.0;
    activeLotSize = (strat.legs && strat.legs[0] && strat.legs[0].lot_size) || 25;

    activeLegs = (strat.legs || []).map((l) => ({
      action: l.action,
      option_type: l.option_type,
      strike: l.strike_price,
      quantity: l.quantity,
      entry_price: l.entry_price,
      iv: l.iv || 16.0,
    }));

    renderLegsTable();
    recalculate();
  }

  function addLeg() {
    activeLegs.push({
      action: 'BUY',
      option_type: 'CE',
      strike: currentSpot,
      quantity: activeLotSize,
      entry_price: 50.0,
      iv: 16.0,
    });
    renderLegsTable();
    recalculate();
  }

  function removeLeg(idx) {
    activeLegs.splice(idx, 1);
    renderLegsTable();
    recalculate();
  }

  function updateLegField(idx, field, value) {
    if (!activeLegs[idx]) return;
    if (field === 'strike' || field === 'quantity' || field === 'entry_price' || field === 'iv') {
      activeLegs[idx][field] = parseFloat(value) || 0;
    } else {
      activeLegs[idx][field] = value;
    }
    recalculate();
  }

  function renderLegsTable() {
    const tbody = document.getElementById('simulator-legs-tbody');
    if (!tbody) return;

    if (activeLegs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:1.5rem; color:var(--text-muted);">No strategy legs configured. Click "+ Add Leg" to build a custom payoff.</td></tr>';
      return;
    }

    tbody.innerHTML = activeLegs
      .map(
        (leg, idx) => `
        <tr>
          <td>
            <select class="select-dropdown" style="padding:0.25rem 0.5rem;" onchange="PayoffSimulatorModule.updateLegField(${idx}, 'action', this.value)">
              <option value="BUY" ${leg.action === 'BUY' ? 'selected' : ''}>BUY</option>
              <option value="SELL" ${leg.action === 'SELL' ? 'selected' : ''}>SELL</option>
            </select>
          </td>
          <td>
            <select class="select-dropdown" style="padding:0.25rem 0.5rem;" onchange="PayoffSimulatorModule.updateLegField(${idx}, 'option_type', this.value)">
              <option value="CE" ${leg.option_type === 'CE' ? 'selected' : ''}>CALL (CE)</option>
              <option value="PE" ${leg.option_type === 'PE' ? 'selected' : ''}>PUT (PE)</option>
            </select>
          </td>
          <td>
            <input type="number" class="symbol-search-input font-mono" style="width:110px; padding:0.25rem 0.5rem;" value="${leg.strike}" step="25" onchange="PayoffSimulatorModule.updateLegField(${idx}, 'strike', this.value)">
          </td>
          <td>
            <input type="number" class="symbol-search-input font-mono" style="width:80px; padding:0.25rem 0.5rem;" value="${leg.quantity}" step="${activeLotSize}" onchange="PayoffSimulatorModule.updateLegField(${idx}, 'quantity', this.value)">
          </td>
          <td>
            <input type="number" class="symbol-search-input font-mono" style="width:90px; padding:0.25rem 0.5rem;" value="${leg.entry_price}" step="0.5" onchange="PayoffSimulatorModule.updateLegField(${idx}, 'entry_price', this.value)">
          </td>
          <td>
            <input type="number" class="symbol-search-input font-mono" style="width:75px; padding:0.25rem 0.5rem;" value="${leg.iv || 16}" step="0.5" onchange="PayoffSimulatorModule.updateLegField(${idx}, 'iv', this.value)">%
          </td>
          <td style="text-align:center;">
            <button class="btn-sm btn-outline" style="color:var(--bearish); border-color:rgba(225,29,72,0.3); padding:0.2rem 0.5rem;" onclick="PayoffSimulatorModule.removeLeg(${idx})" title="Remove Leg">✕</button>
          </td>
        </tr>`
      )
      .join('');
  }

  async function recalculate() {
    if (activeLegs.length === 0) return;

    try {
      const res = await fetch('/api/options/strategies/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: activeSymbol,
          spot: currentSpot,
          lot_size: activeLotSize,
          days_to_expiry: 7,
          legs: activeLegs,
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      updateMetricsDisplay(data);
      renderPayoffChart(data.curve || [], data.breakevens || [], data.spot || currentSpot);
      renderScenarioMatrix(data.scenario_matrix);
    } catch (e) {
      console.warn('Simulation calculation failed:', e);
    }
  }

  function updateMetricsDisplay(data) {
    const isCredit = data.net_debit_credit < 0;
    const debitCreditEl = document.getElementById('sim-val-debit-credit');
    if (debitCreditEl) {
      debitCreditEl.textContent = `${isCredit ? 'Credit' : 'Debit'}: ₹${Math.abs(data.net_debit_credit).toLocaleString('en-IN')}`;
      debitCreditEl.style.color = isCredit ? 'var(--bullish)' : 'var(--accent-gold)';
    }

    const profitEl = document.getElementById('sim-val-max-profit');
    if (profitEl) {
      profitEl.textContent = data.max_profit !== null ? `₹${data.max_profit.toLocaleString('en-IN')}` : 'Unlimited 🚀';
    }

    const lossEl = document.getElementById('sim-val-max-loss');
    if (lossEl) {
      lossEl.textContent = data.max_loss !== null ? `₹${data.max_loss.toLocaleString('en-IN')}` : 'Unlimited ⚠️';
    }

    const beEl = document.getElementById('sim-val-breakevens');
    if (beEl) {
      beEl.textContent = (data.breakevens || []).length > 0 ? data.breakevens.join(', ') : 'None';
    }

    const marginEl = document.getElementById('sim-val-margin');
    if (marginEl) {
      marginEl.textContent = `₹${(data.estimated_margin || 0).toLocaleString('en-IN')}`;
    }

    const frictionEl = document.getElementById('sim-val-friction');
    if (frictionEl) {
      frictionEl.textContent = `₹${(data.transaction_costs?.total_friction || 0).toFixed(1)}`;
    }

    const greeks = data.portfolio_greeks || {};
    const deltaEl = document.getElementById('sim-greek-delta');
    if (deltaEl) deltaEl.textContent = (greeks.delta || 0).toFixed(2);
    const thetaEl = document.getElementById('sim-greek-theta');
    if (thetaEl) thetaEl.textContent = (greeks.theta || 0).toFixed(1);
    const vegaEl = document.getElementById('sim-greek-vega');
    if (vegaEl) vegaEl.textContent = (greeks.vega || 0).toFixed(1);
  }

  function renderPayoffChart(curve, breakevens, spot) {
    const ctx = document.getElementById('chart-payoff');
    if (!ctx) return;

    if (payoffChart) {
      payoffChart.destroy();
      payoffChart = null;
    }

    const labels = curve.map((c) => c.spot);
    const pnlData = curve.map((c) => c.pnl);

    const themeColors = window.getThemeColors ? window.getThemeColors() : {
      textColor: '#475569',
      gridColor: 'rgba(148, 163, 184, 0.15)',
      maxPainLine: '#0284c7',
    };

    payoffChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Net Payoff at Expiration (INR)',
            data: pnlData,
            borderColor: themeColors.maxPainLine || '#0284c7',
            borderWidth: 2.5,
            fill: {
              target: 'origin',
              above: 'rgba(5, 150, 105, 0.12)', // Green for profit
              below: 'rgba(225, 29, 72, 0.12)',  // Red for loss
            },
            tension: 0.1,
            pointRadius: 0,
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
              label: (ctx) => `PnL: ₹${ctx.parsed.y.toLocaleString('en-IN')}`,
            },
          },
        },
        scales: {
          x: {
            grid: { color: themeColors.gridColor },
            ticks: { color: themeColors.textColor, font: { family: 'JetBrains Mono', size: 10 } },
          },
          y: {
            grid: { color: themeColors.gridColor },
            ticks: {
              color: themeColors.textColor,
              font: { family: 'JetBrains Mono', size: 10 },
              callback: (val) => `₹${val.toLocaleString('en-IN')}`,
            },
          },
        },
      },
    });
  }

  function renderScenarioMatrix(scenarioMatrix) {
    const container = document.getElementById('simulator-scenario-container');
    if (!container || !scenarioMatrix) return;

    const spots = scenarioMatrix.spot_shifts || [];
    const ivs = scenarioMatrix.iv_shifts || [];
    const cells = scenarioMatrix.cells || [];

    let headerCols = spots.map((s) => `<th>Spot ${s >= 0 ? '+' : ''}${s}%</th>`).join('');

    let rowsHtml = cells
      .map((row, rIdx) => {
        const ivShift = ivs[rIdx] || 0;
        const cellCols = row
          .map((cell) => {
            const pnl = cell.pnl;
            const bg = pnl >= 0 ? 'rgba(5, 150, 105, 0.12)' : 'rgba(225, 29, 72, 0.12)';
            const color = pnl >= 0 ? 'var(--bullish)' : 'var(--bearish)';
            return `<td style="background:${bg}; color:${color}; font-weight:700; text-align:center; font-family:'JetBrains Mono'; font-size:0.8rem;">
              ${pnl >= 0 ? '+' : ''}₹${pnl.toLocaleString('en-IN')}
            </td>`;
          })
          .join('');

        return `
          <tr>
            <td style="font-weight:700; text-align:left; font-size:0.8rem;">IV ${ivShift >= 0 ? '+' : ''}${ivShift}%</td>
            ${cellCols}
          </tr>`;
      })
      .join('');

    container.innerHTML = `
      <div class="table-responsive">
        <table class="option-table">
          <thead>
            <tr>
              <th style="text-align:left;">Volatility \\ Spot</th>
              ${headerCols}
            </tr>
          </thead>
          <tbody>
            ${rowsHtml}
          </tbody>
        </table>
      </div>
    `;
  }

  return { init, loadFromStrategy, addLeg, removeLeg, updateLegField, recalculate };
})();

