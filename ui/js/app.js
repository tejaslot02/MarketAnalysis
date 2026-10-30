/**
 * Institutional Option Chain & Market Analytics Frontend Engine
 */

const state = {
  symbol: 'NIFTY',
  isEquity: false,
  activeExpiry: '',
  rangeFilter: '15',
  searchQuery: '',
  autoRefreshInterval: 30, // seconds
  autoRefreshTimer: null,
  countdownSeconds: 30,
  activeTab: 'matrix',
  data: null,
  charts: {},
};

// Standard indices list
const INDICES = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY'];

document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  loadData();
  startAutoRefresh();
  checkMarketStatus();
});

/**
 * Event Listeners Initialization
 */
function initEventListeners() {
  // Symbol Pill Selection
  document.querySelectorAll('.symbol-pill').forEach((pill) => {
    pill.addEventListener('click', (e) => {
      document.querySelectorAll('.symbol-pill').forEach((p) => p.classList.remove('active'));
      pill.classList.add('active');
      const sym = pill.dataset.symbol;
      state.symbol = sym;
      state.isEquity = false;
      state.activeExpiry = '';
      document.getElementById('symbol-search').value = '';
      loadData();
    });
  });

  // Custom Symbol Search Input
  const searchInput = document.getElementById('symbol-search');
  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const val = searchInput.value.trim().toUpperCase();
      if (val) {
        document.querySelectorAll('.symbol-pill').forEach((p) => p.classList.remove('active'));
        state.symbol = val;
        state.isEquity = !INDICES.includes(val);
        state.activeExpiry = '';
        loadData();
      }
    }
  });

  // Expiry Dropdown Change
  document.getElementById('expiry-select').addEventListener('change', (e) => {
    state.activeExpiry = e.target.value;
    loadData();
  });

  // Strike Range Filter Buttons
  document.querySelectorAll('.range-pill').forEach((pill) => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.range-pill').forEach((p) => p.classList.remove('active'));
      pill.classList.add('active');
      state.rangeFilter = pill.dataset.range;
      renderMatrix();
      renderCharts();
    });
  });

  // Strike Search Box
  document.getElementById('strike-search').addEventListener('input', (e) => {
    state.searchQuery = e.target.value.trim();
    renderMatrix();
  });

  // Tabs Navigation
  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach((c) => c.classList.remove('active'));
      btn.classList.add('active');
      const tabId = btn.dataset.tab;
      state.activeTab = tabId;
      document.getElementById(tabId).classList.add('active');

      if (tabId === 'charts' || tabId === 'maxpain' || tabId === 'ivsmile') {
        renderCharts();
      } else if (tabId === 'snapshots') {
        loadSnapshots();
      }
    });
  });

  // Manual Refresh Button
  document.getElementById('refresh-btn').addEventListener('click', () => {
    loadData();
  });

  // Auto-Refresh Select
  document.getElementById('auto-refresh-select').addEventListener('change', (e) => {
    state.autoRefreshInterval = parseInt(e.target.value, 10);
    state.countdownSeconds = state.autoRefreshInterval;
    startAutoRefresh();
  });
}

/**
 * Auto-Refresh Timer Management
 */
function startAutoRefresh() {
  if (state.autoRefreshTimer) {
    clearInterval(state.autoRefreshTimer);
    state.autoRefreshTimer = null;
  }
  if (state.autoRefreshInterval <= 0) {
    document.getElementById('countdown-text').textContent = 'Off';
    return;
  }

  state.countdownSeconds = state.autoRefreshInterval;
  state.autoRefreshTimer = setInterval(() => {
    state.countdownSeconds--;
    if (state.countdownSeconds <= 0) {
      state.countdownSeconds = state.autoRefreshInterval;
      loadData(true); // Silent refresh
    }
    document.getElementById('countdown-text').textContent = `${state.countdownSeconds}s`;
  }, 1000);
}

/**
 * Fetch Live Data from Backend API
 */
async function loadData(silent = false) {
  const overlay = document.getElementById('loading-overlay');
  if (!silent) overlay.classList.add('active');

  try {
    const params = new URLSearchParams({
      symbol: state.symbol,
      equity: state.isEquity ? 'true' : 'false',
    });
    if (state.activeExpiry) {
      params.append('expiry', state.activeExpiry);
    }

    const response = await fetch(`/api/option-chain?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    const json = await response.json();
    state.data = json;

    updateHeaderMetrics(json);
    populateExpiries(json.expiry_dates, json.selected_expiry);
    renderMatrix();
    renderCharts();
  } catch (err) {
    console.error('Failed to load option chain:', err);
    alert(`Could not fetch data for ${state.symbol}: ${err.message}`);
  } finally {
    if (!silent) overlay.classList.remove('active');
  }
}

/**
 * Populate Top Executive Metric Cards
 */
function updateHeaderMetrics(data) {
  const spot = data.underlying_value || 0;
  const metrics = data.metrics || {};

  // 1. Spot Price
  document.getElementById('val-spot').textContent = formatNumber(spot, 2);
  document.getElementById('val-timestamp').textContent = `NSE India: ${data.timestamp || 'Real-time'}`;

  // 2. ATM Strike
  const atm = metrics.atm_strike || 0;
  document.getElementById('val-atm').textContent = formatNumber(atm, 1);
  const diff = spot > 0 ? (atm - spot).toFixed(1) : 0;
  const diffSign = diff >= 0 ? `+${diff}` : `${diff}`;
  document.getElementById('sub-atm').textContent = `Distance: ${diffSign} pts`;

  // 3. Max Pain Strike
  const maxPain = metrics.max_pain_strike || 0;
  document.getElementById('val-maxpain').textContent = formatNumber(maxPain, 1);
  const painShift = (maxPain - spot).toFixed(1);
  const painShiftSign = painShift >= 0 ? `+${painShift}` : `${painShift}`;
  document.getElementById('sub-maxpain').textContent = `Bias to Spot: ${painShiftSign} pts`;

  // 4. Put-Call Ratio (PCR)
  const pcrOI = metrics.pcr_oi || 0;
  const pcrVol = metrics.pcr_volume || 0;
  document.getElementById('val-pcr').textContent = pcrOI.toFixed(2);
  const pcrSub = document.getElementById('sub-pcr');

  if (pcrOI >= 1.2) {
    pcrSub.textContent = 'Bullish (>1.2)';
    pcrSub.className = 'metric-sub bullish';
  } else if (pcrOI <= 0.8) {
    pcrSub.textContent = 'Bearish (<0.8)';
    pcrSub.className = 'metric-sub bearish';
  } else {
    pcrSub.textContent = 'Neutral (0.8 - 1.2)';
    pcrSub.className = 'metric-sub gold';
  }
  document.getElementById('footer-pcr-vol').textContent = `PCR (Vol): ${pcrVol.toFixed(2)}`;

  // 5. Total Open Interest Ratio
  const totCeOi = metrics.total_ce_oi || 0;
  const totPeOi = metrics.total_pe_oi || 0;
  const sumOi = totCeOi + totPeOi;
  const peOiPct = sumOi > 0 ? (totPeOi / sumOi) * 100 : 50;

  document.getElementById('val-total-oi').textContent = formatCompact(sumOi);
  document.getElementById('bar-oi-fill').style.width = `${peOiPct}%`;
  document.getElementById('footer-ce-oi').textContent = `Calls: ${formatCompact(totCeOi)}`;
  document.getElementById('footer-pe-oi').textContent = `Puts: ${formatCompact(totPeOi)}`;

  // Key Support & Resistance Callouts in Banner
  updateSupportResistanceCallout(data.chain || []);
}

/**
 * Detect & Update Support / Resistance Callouts
 */
function updateSupportResistanceCallout(chain) {
  if (!chain || chain.length === 0) return;

  let maxCallOi = -1;
  let resStrike = null;
  let maxPutOi = -1;
  let supStrike = null;

  chain.forEach((row) => {
    if (row.CE_OI > maxCallOi) {
      maxCallOi = row.CE_OI;
      resStrike = row.strikePrice;
    }
    if (row.PE_OI > maxPutOi) {
      maxPutOi = row.PE_OI;
      supStrike = row.strikePrice;
    }
  });

  const resEl = document.getElementById('banner-resistance');
  const supEl = document.getElementById('banner-support');

  if (resEl) resEl.textContent = `${resStrike || 'N/A'} (OI: ${formatCompact(maxCallOi)})`;
  if (supEl) supEl.textContent = `${supStrike || 'N/A'} (OI: ${formatCompact(maxPutOi)})`;
}

/**
 * Populate Expiries Dropdown
 */
function populateExpiries(expiries, selected) {
  const select = document.getElementById('expiry-select');
  const currentVal = state.activeExpiry || selected || (expiries && expiries[0]);

  select.innerHTML = '';
  (expiries || []).forEach((exp) => {
    const opt = document.createElement('option');
    opt.value = exp;
    opt.textContent = exp;
    if (exp === currentVal) {
      opt.selected = true;
    }
    select.appendChild(opt);
  });
  state.activeExpiry = select.value;
}

/**
 * Render Option Chain Matrix Table
 */
function renderMatrix() {
  if (!state.data || !state.data.chain) return;

  const tbody = document.getElementById('matrix-tbody');
  tbody.innerHTML = '';

  let chain = [...state.data.chain];
  const spot = state.data.underlying_value || 0;
  const atm = state.data.metrics?.atm_strike || 0;

  // Filter by Strike Range around ATM
  if (state.rangeFilter !== 'all' && atm > 0) {
    const count = parseInt(state.rangeFilter, 10);
    // Find index of ATM
    const atmIdx = chain.findIndex((r) => Math.abs(r.strikePrice - atm) < 0.1);
    if (atmIdx !== -1) {
      const start = Math.max(0, atmIdx - count);
      const end = Math.min(chain.length, atmIdx + count + 1);
      chain = chain.slice(start, end);
    }
  }

  // Filter by Search Query
  if (state.searchQuery) {
    chain = chain.filter((r) => String(r.strikePrice).includes(state.searchQuery));
  }

  // Compute Maximum OI and Volume for relative distribution bar widths
  let maxCeOi = 1;
  let maxPeOi = 1;
  chain.forEach((r) => {
    if (r.CE_OI > maxCeOi) maxCeOi = r.CE_OI;
    if (r.PE_OI > maxPeOi) maxPeOi = r.PE_OI;
  });

  const fragment = document.createDocumentFragment();

  chain.forEach((row) => {
    const strike = row.strikePrice;
    const isAtm = Math.abs(strike - atm) < 0.1;
    const isCallItm = strike < spot;
    const isPutItm = strike > spot;

    const tr = document.createElement('tr');
    if (isAtm) tr.classList.add('tr-atm');

    // CE OI Relative %
    const ceOiWidth = ((row.CE_OI || 0) / maxCeOi) * 100;
    // PE OI Relative %
    const peOiWidth = ((row.PE_OI || 0) / maxPeOi) * 100;

    // Call columns
    const ceChgClass = row.CE_Change >= 0 ? 'text-bullish' : 'text-bearish';
    const peChgClass = row.PE_Change >= 0 ? 'text-bullish' : 'text-bearish';

    tr.innerHTML = `
      <!-- CALLS SIDE -->
      <td class="oi-bar-cell ${isCallItm ? 'td-call-itm' : ''}">
        <div class="oi-bar oi-bar-call" style="width: ${ceOiWidth}%"></div>
        <span class="oi-val text-bold">${formatNumber(row.CE_OI)}</span>
      </td>
      <td class="${isCallItm ? 'td-call-itm' : ''} ${row.CE_Chg_OI >= 0 ? 'text-bullish' : 'text-bearish'}">
        ${formatNumber(row.CE_Chg_OI)}
      </td>
      <td class="${isCallItm ? 'td-call-itm' : ''}">${formatNumber(row.CE_Volume)}</td>
      <td class="${isCallItm ? 'td-call-itm' : ''} text-muted">${row.CE_IV ? row.CE_IV.toFixed(1) : '-'}</td>
      <td class="${isCallItm ? 'td-call-itm' : ''} text-bold">${row.CE_LTP ? row.CE_LTP.toFixed(2) : '-'}</td>
      <td class="${isCallItm ? 'td-call-itm' : ''} ${ceChgClass}">${formatChange(row.CE_Change)}</td>

      <!-- STRIKE (CENTER) -->
      <td class="td-strike">
        ${formatNumber(strike, 1)}
        ${isAtm ? '<span class="atm-badge">ATM</span>' : ''}
      </td>

      <!-- PUTS SIDE -->
      <td class="${isPutItm ? 'td-put-itm' : ''} ${peChgClass}">${formatChange(row.PE_Change)}</td>
      <td class="${isPutItm ? 'td-put-itm' : ''} text-bold">${row.PE_LTP ? row.PE_LTP.toFixed(2) : '-'}</td>
      <td class="${isPutItm ? 'td-put-itm' : ''} text-muted">${row.PE_IV ? row.PE_IV.toFixed(1) : '-'}</td>
      <td class="${isPutItm ? 'td-put-itm' : ''}">${formatNumber(row.PE_Volume)}</td>
      <td class="${isPutItm ? 'td-put-itm' : ''} ${row.PE_Chg_OI >= 0 ? 'text-bullish' : 'text-bearish'}">
        ${formatNumber(row.PE_Chg_OI)}
      </td>
      <td class="oi-bar-cell ${isPutItm ? 'td-put-itm' : ''}">
        <div class="oi-bar oi-bar-put" style="width: ${peOiWidth}%"></div>
        <span class="oi-val text-bold">${formatNumber(row.PE_OI)}</span>
      </td>
    `;

    fragment.appendChild(tr);
  });

  tbody.appendChild(fragment);
}

/**
 * Render Analytics Charts using Chart.js
 */
function renderCharts() {
  if (!state.data || !state.data.chain) return;

  const chain = [...state.data.chain];
  const atm = state.data.metrics?.atm_strike || 0;

  // Filter for charts: ±15 strikes around ATM to keep charts sharp and readable
  let chartChain = chain;
  if (atm > 0) {
    const atmIdx = chain.findIndex((r) => Math.abs(r.strikePrice - atm) < 0.1);
    if (atmIdx !== -1) {
      const start = Math.max(0, atmIdx - 15);
      const end = Math.min(chain.length, atmIdx + 16);
      chartChain = chain.slice(start, end);
    }
  }

  const strikes = chartChain.map((r) => r.strikePrice);
  const ceOi = chartChain.map((r) => r.CE_OI);
  const peOi = chartChain.map((r) => r.PE_OI);
  const ceChgOi = chartChain.map((r) => r.CE_Chg_OI);
  const peChgOi = chartChain.map((r) => r.PE_Chg_OI);
  const ceIv = chartChain.map((r) => (r.CE_IV > 0 ? r.CE_IV : null));
  const peIv = chartChain.map((r) => (r.PE_IV > 0 ? r.PE_IV : null));

  // 1. OI Distribution Chart
  buildOiChart(strikes, ceOi, peOi, atm);

  // 2. Change in OI Chart
  buildOiChgChart(strikes, ceChgOi, peChgOi, atm);

  // 3. Max Pain Curve Chart
  buildMaxPainChart(chain, state.data.underlying_value, state.data.metrics?.max_pain_strike);

  // 4. IV Smile Chart
  buildIvSmileChart(strikes, ceIv, peIv, atm);
}

/**
 * Chart 1: Open Interest Grouped Bars
 */
function buildOiChart(labels, callData, putData, atm) {
  const ctx = document.getElementById('chart-oi');
  if (!ctx) return;

  if (state.charts.oi) state.charts.oi.destroy();

  state.charts.oi = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Call OI (Resistance)',
          data: callData,
          backgroundColor: 'rgba(56, 189, 248, 0.75)',
          borderColor: '#38bdf8',
          borderWidth: 1,
          borderRadius: 4,
        },
        {
          label: 'Put OI (Support)',
          data: putData,
          backgroundColor: 'rgba(244, 63, 94, 0.75)',
          borderColor: '#f43f5e',
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    },
    options: getChartOptions('Open Interest Distribution by Strike'),
  });
}

/**
 * Chart 2: Change in OI (Buildup & Unwinding)
 */
function buildOiChgChart(labels, callChg, putChg, atm) {
  const ctx = document.getElementById('chart-oi-chg');
  if (!ctx) return;

  if (state.charts.oiChg) state.charts.oiChg.destroy();

  state.charts.oiChg = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Call Chg in OI',
          data: callChg,
          backgroundColor: 'rgba(56, 189, 248, 0.75)',
          borderRadius: 4,
        },
        {
          label: 'Put Chg in OI',
          data: putChg,
          backgroundColor: 'rgba(244, 63, 94, 0.75)',
          borderRadius: 4,
        },
      ],
    },
    options: getChartOptions('Intraday Change in Open Interest'),
  });
}

/**
 * Chart 3: Max Pain Settlement Curve
 */
function buildMaxPainChart(fullChain, spot, maxPainStrike) {
  const ctx = document.getElementById('chart-maxpain');
  if (!ctx || !fullChain) return;

  const strikes = fullChain.map((r) => r.strikePrice);
  const lossData = strikes.map((target) => {
    let loss = 0;
    fullChain.forEach((r) => {
      // Calls writer payout: max(0, target - strike) * CE_OI
      if (target > r.strikePrice) loss += (target - r.strikePrice) * (r.CE_OI || 0);
      // Puts writer payout: max(0, strike - target) * PE_OI
      if (r.strikePrice > target) loss += (r.strikePrice - target) * (r.PE_OI || 0);
    });
    return loss;
  });

  if (state.charts.maxPain) state.charts.maxPain.destroy();

  state.charts.maxPain = new Chart(ctx, {
    type: 'line',
    data: {
      labels: strikes,
      datasets: [
        {
          label: 'Total Option Writer Payout Loss (INR)',
          data: lossData,
          fill: true,
          borderColor: '#f59e0b',
          backgroundColor: 'rgba(245, 158, 11, 0.1)',
          borderWidth: 2,
          tension: 0.3,
          pointRadius: strikes.map((s) => (s === maxPainStrike ? 6 : 0)),
          pointBackgroundColor: '#fbbf24',
        },
      ],
    },
    options: getChartOptions('Option Writers Loss Curve (Max Pain at minimum liability)'),
  });
}

/**
 * Chart 4: Implied Volatility (IV) Smile
 */
function buildIvSmileChart(labels, ceIv, peIv, atm) {
  const ctx = document.getElementById('chart-iv');
  if (!ctx) return;

  if (state.charts.ivSmile) state.charts.ivSmile.destroy();

  state.charts.ivSmile = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Call IV',
          data: ceIv,
          borderColor: '#38bdf8',
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 2,
        },
        {
          label: 'Put IV',
          data: peIv,
          borderColor: '#f43f5e',
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 2,
        },
      ],
    },
    options: getChartOptions('Implied Volatility (IV) Smile & Skew'),
  });
}

/**
 * Standard Dark Theme Chart.js Options
 */
function getChartOptions(titleText) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: '#94a3b8',
          font: { family: 'Outfit', size: 12 },
        },
      },
      tooltip: {
        backgroundColor: '#0f172a',
        titleColor: '#f8fafc',
        bodyColor: '#cbd5e1',
        borderColor: 'rgba(255,255,255,0.1)',
        borderWidth: 1,
        padding: 10,
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(255, 255, 255, 0.04)' },
        ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } },
      },
      y: {
        grid: { color: 'rgba(255, 255, 255, 0.04)' },
        ticks: {
          color: '#64748b',
          font: { family: 'JetBrains Mono', size: 10 },
          callback: (val) => formatCompact(val),
        },
      },
    },
  };
}

/**
 * Load SQLite Snapshot History
 */
async function loadSnapshots() {
  const tbody = document.getElementById('snapshots-tbody');
  tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">Loading historical snapshots...</td></tr>';

  try {
    const res = await fetch(`/api/snapshots?symbol=${state.symbol}`);
    const rows = await res.json();
    tbody.innerHTML = '';

    if (!rows || rows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No snapshots recorded yet in SQLite.</td></tr>';
      return;
    }

    rows.forEach((r) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="text-align:left;">${r.recorded_at || r.timestamp}</td>
        <td>${r.symbol}</td>
        <td class="text-bold">${formatNumber(r.underlying_value, 2)}</td>
        <td>${formatNumber(r.atm_strike, 1)}</td>
        <td class="text-bullish">${formatNumber(r.max_pain_strike, 1)}</td>
        <td class="text-bold">${r.pcr_oi ? r.pcr_oi.toFixed(2) : '-'}</td>
        <td>${formatCompact(r.total_ce_oi + r.total_pe_oi)}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="7" style="color:var(--bearish);text-align:center;">Error: ${e.message}</td></tr>`;
  }
}

/**
 * Check Market Operational Status
 */
async function checkMarketStatus() {
  try {
    const res = await fetch('/api/market-status');
    const data = await res.json();
    const statusBadge = document.getElementById('market-badge');
    const statusText = document.getElementById('market-status-text');

    const capMkt = (data.marketState || []).find((m) => m.market === 'Capital Market');
    const isOpen = capMkt && capMkt.marketStatus && capMkt.marketStatus.toLowerCase() === 'open';

    if (isOpen) {
      statusBadge.classList.remove('closed');
      statusText.textContent = 'NSE Market Open';
    } else {
      statusBadge.classList.add('closed');
      statusText.textContent = 'NSE Market Closed';
    }
  } catch (e) {
    console.warn('Could not probe market status:', e);
  }
}

/**
 * Trigger Data Export
 */
function exportData(format) {
  const params = new URLSearchParams({
    symbol: state.symbol,
    format: format,
    expiry: state.activeExpiry,
  });
  window.location.href = `/api/export?${params.toString()}`;
}

/**
 * Numeric Formatting Helpers
 */
function formatNumber(num, decimals = 0) {
  if (num === null || num === undefined || isNaN(num)) return '-';
  return Number(num).toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function formatCompact(num) {
  if (num === null || num === undefined || isNaN(num)) return '-';
  if (num >= 10000000) return (num / 10000000).toFixed(2) + ' Cr';
  if (num >= 100000) return (num / 100000).toFixed(2) + ' L';
  if (num >= 1000) return (num / 1000).toFixed(1) + ' k';
  return String(num);
}

function formatChange(val) {
  if (val === null || val === undefined || isNaN(val)) return '-';
  const prefix = val > 0 ? '+' : '';
  return `${prefix}${val.toFixed(2)}`;
}
