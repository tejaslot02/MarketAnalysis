/**
 * Institutional Option Chain & Market Analytics Frontend Engine
 */

const state = {
  theme: 'pastel-light',
  symbol: 'NIFTY',
  previousValidSymbol: 'NIFTY',
  isEquity: false,
  previousValidIsEquity: false,
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
  initTheme();
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

  // Top-Level Section Switcher (Option Chain Terminal vs Options Intelligence)
  document.querySelectorAll('.section-nav-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.section-nav-btn').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.view-panel').forEach((p) => {
        p.classList.remove('active');
        p.style.display = 'none';
      });
      btn.classList.add('active');
      const sectionId = btn.dataset.section;
      const targetPanel = document.getElementById(sectionId);
      if (targetPanel) {
        targetPanel.classList.add('active');
        targetPanel.style.display = 'block';
      }

      if (sectionId === 'view-intelligence') {
        if (window.MarketOverviewModule) window.MarketOverviewModule.load(state.symbol);
        if (window.StrategyScannerModule) window.StrategyScannerModule.load(state.symbol);
      }
    });
  });

  // Intelligence Sub-Tabs Navigation
  document.querySelectorAll('[data-inteltab]').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-inteltab]').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.intel-tab-content').forEach((c) => {
        c.classList.remove('active');
        c.style.display = 'none';
      });
      btn.classList.add('active');
      const tabId = btn.dataset.inteltab;
      const targetTab = document.getElementById(tabId);
      if (targetTab) {
        targetTab.classList.add('active');
        targetTab.style.display = 'block';
      }

      if (tabId === 'intel-overview' && window.MarketOverviewModule) {
        window.MarketOverviewModule.load(state.symbol);
      } else if (tabId === 'intel-scanner' && window.StrategyScannerModule) {
        window.StrategyScannerModule.load(state.symbol);
      } else if (tabId === 'intel-simulator' && window.PayoffSimulatorModule) {
        window.PayoffSimulatorModule.init();
      } else if (tabId === 'intel-backtest' && window.BacktestingModule) {
        window.BacktestingModule.init();
      } else if (tabId === 'intel-alerts' && window.AlertsModule) {
        window.AlertsModule.init();
      }
    });
  });

  // Option Chain Terminal Tabs Navigation
  document.querySelectorAll('#view-terminal .tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#view-terminal .tab-btn').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('#view-terminal .tab-content').forEach((c) => c.classList.remove('active'));
      btn.classList.add('active');
      const tabId = btn.dataset.tab;
      state.activeTab = tabId;
      const targetTab = document.getElementById(tabId);
      if (targetTab) targetTab.classList.add('active');

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

  // Theme Selector Dropdown
  const themeSelect = document.getElementById('theme-select');
  if (themeSelect) {
    themeSelect.addEventListener('change', (e) => {
      applyTheme(e.target.value);
    });
  }
}

/**
 * Auto-Refresh Timer Management with Wall-Clock Drift Resistance
 */
let nextRefreshTime = 0;

function startAutoRefresh() {
  if (state.autoRefreshTimer) {
    clearInterval(state.autoRefreshTimer);
    state.autoRefreshTimer = null;
  }
  if (state.autoRefreshInterval <= 0) {
    const el = document.getElementById('countdown-text');
    if (el) el.textContent = 'Off';
    return;
  }

  nextRefreshTime = Date.now() + state.autoRefreshInterval * 1000;
  state.countdownSeconds = state.autoRefreshInterval;
  const el = document.getElementById('countdown-text');
  if (el) el.textContent = `${state.countdownSeconds}s`;

  state.autoRefreshTimer = setInterval(() => {
    const remaining = Math.max(0, Math.ceil((nextRefreshTime - Date.now()) / 1000));
    state.countdownSeconds = remaining;
    if (remaining <= 0) {
      nextRefreshTime = Date.now() + state.autoRefreshInterval * 1000;
      state.countdownSeconds = state.autoRefreshInterval;
      loadData(true); // Silent refresh
    }
    const txtEl = document.getElementById('countdown-text');
    if (txtEl) txtEl.textContent = `${state.countdownSeconds}s`;
  }, 1000);
}

// Ensure backgrounded tabs refresh immediately if expired upon regain of focus
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && state.autoRefreshInterval > 0 && nextRefreshTime > 0) {
    if (Date.now() >= nextRefreshTime) {
      nextRefreshTime = Date.now() + state.autoRefreshInterval * 1000;
      loadData(true);
    }
  }
});

/**
 * Fetch Live Data from Backend API
 */
async function loadData(silent = false) {
  const overlay = document.getElementById('loading-overlay');
  if (!silent) overlay.classList.add('active');

  const requestedSymbol = state.symbol;
  const requestedIsEquity = state.isEquity;

  try {
    const params = new URLSearchParams({
      symbol: requestedSymbol,
      equity: requestedIsEquity ? 'true' : 'false',
    });
    if (state.activeExpiry) {
      params.append('expiry', state.activeExpiry);
    }

    const response = await fetch(`/api/option-chain?${params.toString()}`);
    let json;
    try {
      json = await response.json();
    } catch (e) {
      json = { error: `HTTP ${response.status} ${response.statusText}` };
    }

    if (!response.ok) {
      const errorMsg = json.error || `Server returned HTTP ${response.status}`;
      throw new Error(errorMsg);
    }

    // Success: commit state
    state.data = json;
    state.previousValidSymbol = requestedSymbol;
    state.previousValidIsEquity = requestedIsEquity;

    updateHeaderMetrics(json);
    populateExpiries(json.expiry_dates, json.selected_expiry);
    renderMatrix();
    renderCharts();

    // Synchronize Options Intelligence views if active
    const intelPanel = document.getElementById('view-intelligence');
    if (intelPanel && intelPanel.style.display !== 'none') {
      if (window.MarketOverviewModule) window.MarketOverviewModule.load(requestedSymbol);
      if (window.StrategyScannerModule) window.StrategyScannerModule.load(requestedSymbol);
    }
  } catch (err) {
    console.warn(`Failed to load option chain for ${requestedSymbol}:`, err.message);

    // Revert to last known valid symbol so auto-refresh loop stays healthy
    state.symbol = state.previousValidSymbol || 'NIFTY';
    state.isEquity = state.previousValidIsEquity || false;
    syncSymbolUI(state.symbol);

    if (!silent) {
      showNotification(
        err.message,
        'error',
        `No Option Chain for ${requestedSymbol}`
      );
    }
  } finally {
    if (!silent) overlay.classList.remove('active');
  }
}

/**
 * Display Non-Blocking Toast Notification
 */
function showNotification(message, type = 'info', title = '') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  const iconMap = {
    error: '⚠️',
    warning: '⚡',
    info: '💡',
    success: '✅',
  };
  const icon = iconMap[type] || 'ℹ️';

  toast.innerHTML = `
    <span class="toast-icon">${icon}</span>
    <div class="toast-body">
      ${title ? `<div class="toast-title">${title}</div>` : ''}
      <div>${message}</div>
    </div>
    <button class="toast-close" title="Dismiss">&times;</button>
  `;

  const closeBtn = toast.querySelector('.toast-close');
  closeBtn.addEventListener('click', () => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 250);
  });

  container.appendChild(toast);

  // Auto remove after 5.5s
  setTimeout(() => {
    if (toast.parentElement) {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 250);
    }
  }, 5500);
}

/**
 * Synchronize Symbol UI Elements (Pills & Search input)
 */
function syncSymbolUI(symbol) {
  document.querySelectorAll('.symbol-pill').forEach((p) => {
    if (p.dataset.symbol === symbol) {
      p.classList.add('active');
    } else {
      p.classList.remove('active');
    }
  });
  const searchInput = document.getElementById('symbol-search');
  if (searchInput) {
    searchInput.value = INDICES.includes(symbol) ? '' : symbol;
  }
}

/**
 * Populate Top Executive Metric Cards
 */
function updateHeaderMetrics(data) {
  const spot = data.underlying_value || 0;
  const metrics = data.metrics || {};
  const isCashEquity = data.is_fo_symbol === false || !!data.cash_equity_notice;

  // 1. Spot Price
  document.getElementById('val-spot').textContent = formatNumber(spot, 2);
  const companyPrefix = data.company_name ? `${data.company_name} | ` : '';
  document.getElementById('val-timestamp').textContent = `NSE India: ${companyPrefix}${data.timestamp || 'Real-time'}`;

  // 2. ATM Strike
  const atm = metrics.atm_strike || 0;
  if (isCashEquity) {
    document.getElementById('val-atm').textContent = 'Cash Only';
    document.getElementById('sub-atm').textContent = `Series: ${data.equity_quote?.series || 'EQ'}`;
  } else {
    document.getElementById('val-atm').textContent = formatNumber(atm, 1);
    const diff = spot > 0 ? (atm - spot).toFixed(1) : 0;
    const diffSign = diff >= 0 ? `+${diff}` : `${diff}`;
    document.getElementById('sub-atm').textContent = `Distance: ${diffSign} pts`;
  }

  // 3. Max Pain Strike
  const maxPain = metrics.max_pain_strike || 0;
  if (isCashEquity) {
    document.getElementById('val-maxpain').textContent = 'N/A';
    document.getElementById('sub-maxpain').textContent = 'No F&O Listing';
  } else {
    document.getElementById('val-maxpain').textContent = formatNumber(maxPain, 1);
    const painShift = (maxPain - spot).toFixed(1);
    const painShiftSign = painShift >= 0 ? `+${painShift}` : `${painShift}`;
    document.getElementById('sub-maxpain').textContent = `Bias to Spot: ${painShiftSign} pts`;
  }

  // 4. Put-Call Ratio (PCR)
  if (isCashEquity) {
    document.getElementById('val-pcr').textContent = 'N/A';
    const pcrSub = document.getElementById('sub-pcr');
    pcrSub.textContent = 'Cash Equity';
    pcrSub.className = 'metric-sub gold';
    const w52High = data.equity_quote?.week52_high;
    const w52Low = data.equity_quote?.week52_low;
    document.getElementById('footer-pcr-vol').textContent = w52High
      ? `52W: ₹${formatNumber(w52Low)} - ₹${formatNumber(w52High)}`
      : 'Non-Derivative';
  } else {
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
  }

  // 5. Total Open Interest Ratio
  if (isCashEquity) {
    document.getElementById('val-total-oi').textContent = 'N/A';
    document.getElementById('bar-oi-fill').style.width = '0%';
    const dHigh = data.equity_quote?.day_high;
    const dLow = data.equity_quote?.day_low;
    document.getElementById('footer-ce-oi').textContent = dHigh
      ? `Day H/L: ₹${formatNumber(dLow)} - ₹${formatNumber(dHigh)}`
      : 'No OI';
    document.getElementById('footer-pe-oi').textContent = `Vol: ${formatCompact(data.equity_quote?.total_traded_volume || 0)}`;
  } else {
    const totCeOi = metrics.total_ce_oi || 0;
    const totPeOi = metrics.total_pe_oi || 0;
    const sumOi = totCeOi + totPeOi;
    const peOiPct = sumOi > 0 ? (totPeOi / sumOi) * 100 : 50;

    document.getElementById('val-total-oi').textContent = formatCompact(sumOi);
    document.getElementById('bar-oi-fill').style.width = `${peOiPct}%`;
    document.getElementById('footer-ce-oi').textContent = `Calls: ${formatCompact(totCeOi)}`;
    document.getElementById('footer-pe-oi').textContent = `Puts: ${formatCompact(totPeOi)}`;
  }

  // Key Support & Resistance Callouts in Banner
  if (isCashEquity) {
    const resEl = document.getElementById('banner-resistance');
    const supEl = document.getElementById('banner-support');
    const biasEl = document.getElementById('banner-bias');
    if (resEl) resEl.textContent = `NSE Cash Market (${data.equity_quote?.series || 'EQ'})`;
    if (supEl) supEl.textContent = `Spot: ₹${formatNumber(spot, 2)}`;
    if (biasEl) biasEl.textContent = 'Cash Equity (Options unlisted on NSE)';
  } else {
    updateSupportResistanceCallout(data.chain || []);
  }
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
  select.innerHTML = '';

  if (!expiries || expiries.length === 0) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'No active expiries (Cash Equity)';
    select.appendChild(opt);
    state.activeExpiry = '';
    return;
  }

  const currentVal = state.activeExpiry || selected || (expiries && expiries[0]);
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
  if (!state.data) return;

  const tbody = document.getElementById('matrix-tbody');
  tbody.innerHTML = '';

  let chain = state.data.chain ? [...state.data.chain] : [];
  const spot = state.data.underlying_value || 0;
  const atm = state.data.metrics?.atm_strike || 0;
  const isCashEquity = state.data.is_fo_symbol === false || !!state.data.cash_equity_notice;

  if (chain.length === 0) {
    if (isCashEquity) {
      const company = state.data.company_name || state.symbol;
      const ltp = state.data.underlying_value || 0;
      tbody.innerHTML = `
        <tr>
          <td colspan="13" style="text-align:center; padding: 3rem 1.5rem;">
            <div style="display:inline-block; max-width: 620px; text-align: center;">
              <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">🏢</div>
              <h3 style="font-size: 1.15rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.4rem;">
                ${company} (${state.symbol}) &mdash; Active NSE Cash Equity
              </h3>
              <p style="font-size: 0.88rem; color: var(--text-secondary); line-height: 1.5; margin-bottom: 1rem;">
                Spot Price: <strong style="color:var(--text-primary);">₹${formatNumber(ltp, 2)}</strong> | Series: <strong style="color:var(--text-primary);">${state.data.equity_quote?.series || 'EQ'}</strong>
              </p>
              <div style="background: var(--bg-tertiary); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 0.85rem 1.1rem; margin-bottom: 1.25rem; font-size: 0.82rem; color: var(--text-secondary); text-align: left; line-height: 1.5;">
                ℹ️ <strong>Why are there no option strikes?</strong><br>
                ${state.symbol} trades in the <strong>NSE Cash Market segment</strong>. Only ~180 large/mid-cap securities approved by SEBI trade in the <strong>Derivatives (Futures & Options)</strong> segment with active option chains.
              </div>
              <div style="display:flex; justify-content:center; align-items:center; gap: 0.5rem; flex-wrap: wrap;">
                <span style="font-size:0.8rem; color: var(--text-muted);">Explore F&O Option Chains:</span>
                <button class="btn-icon" onclick="selectQuickStock('RELIANCE')">RELIANCE</button>
                <button class="btn-icon" onclick="selectQuickStock('TCS')">TCS</button>
                <button class="btn-icon" onclick="selectQuickStock('INFY')">INFY</button>
                <button class="btn-icon" onclick="selectQuickStock('NIFTY')">NIFTY</button>
              </div>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = `
      <tr>
        <td colspan="13" style="text-align:center; padding: 2.5rem; color: var(--text-muted);">
          No option chain records available for ${state.symbol}.
        </td>
      </tr>
    `;
    return;
  }

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
  if (!state.data) return;

  const chain = state.data.chain ? [...state.data.chain] : [];

  if (chain.length === 0) {
    if (state.charts.oi) { state.charts.oi.destroy(); state.charts.oi = null; }
    if (state.charts.oiChg) { state.charts.oiChg.destroy(); state.charts.oiChg = null; }
    if (state.charts.maxPain) { state.charts.maxPain.destroy(); state.charts.maxPain = null; }
    if (state.charts.ivSmile) { state.charts.ivSmile.destroy(); state.charts.ivSmile = null; }
    return;
  }

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
 * Quick Selector to switch to popular F&O stocks or indices
 */
window.selectQuickStock = function (sym) {
  if (INDICES.includes(sym)) {
    document.querySelectorAll('.symbol-pill').forEach((p) => {
      if (p.dataset.symbol === sym) p.classList.add('active');
      else p.classList.remove('active');
    });
    state.symbol = sym;
    state.isEquity = false;
    const searchInput = document.getElementById('symbol-search');
    if (searchInput) searchInput.value = '';
  } else {
    document.querySelectorAll('.symbol-pill').forEach((p) => p.classList.remove('active'));
    state.symbol = sym;
    state.isEquity = true;
    const searchInput = document.getElementById('symbol-search');
    if (searchInput) searchInput.value = sym;
  }
  state.activeExpiry = '';
  loadData();
};

/**
 * Initialize Theme from Storage or Default to Pastel Light
 */
function initTheme() {
  const savedTheme = localStorage.getItem('market_terminal_theme') || 'pastel-light';
  state.theme = savedTheme;
  applyTheme(savedTheme, false);
}

/**
 * Switch Theme dynamically and refresh Chart palettes
 */
function applyTheme(themeName, updateCharts = true) {
  state.theme = themeName;
  document.documentElement.setAttribute('data-theme', themeName);
  localStorage.setItem('market_terminal_theme', themeName);

  const themeSelect = document.getElementById('theme-select');
  if (themeSelect && themeSelect.value !== themeName) {
    themeSelect.value = themeName;
  }

  if (updateCharts && state.data) {
    renderCharts();
  }
}

/**
 * Active Theme Color Tokens for Canvas Charts
 */
function getThemeColors() {
  const theme = state.theme || document.documentElement.getAttribute('data-theme') || 'pastel-light';

  if (theme === 'pastel-light') {
    return {
      callColor: 'rgba(125, 211, 252, 0.85)',
      callBorder: '#38bdf8',
      putColor: 'rgba(253, 164, 175, 0.85)',
      putBorder: '#fb7185',
      maxPainLine: '#d97706',
      maxPainFill: 'rgba(251, 191, 36, 0.22)',
      maxPainPoint: '#fbbf24',
      ivCallLine: '#0284c7',
      ivPutLine: '#e11d48',
      textColor: '#475569',
      gridColor: 'rgba(148, 163, 184, 0.15)',
      tooltipBg: '#ffffff',
      tooltipTitle: '#0f172a',
      tooltipBody: '#334155',
      tooltipBorder: 'rgba(148, 163, 184, 0.25)',
    };
  } else if (theme === 'pastel-dark') {
    return {
      callColor: 'rgba(125, 211, 252, 0.75)',
      callBorder: '#7dd3fc',
      putColor: 'rgba(253, 164, 175, 0.75)',
      putBorder: '#fda4af',
      maxPainLine: '#fde047',
      maxPainFill: 'rgba(253, 224, 71, 0.18)',
      maxPainPoint: '#fef08a',
      ivCallLine: '#7dd3fc',
      ivPutLine: '#fda4af',
      textColor: '#94a3b8',
      gridColor: 'rgba(255, 255, 255, 0.06)',
      tooltipBg: '#1e2233',
      tooltipTitle: '#f8fafc',
      tooltipBody: '#cbd5e1',
      tooltipBorder: 'rgba(255, 255, 255, 0.1)',
    };
  } else {
    // Classic dark
    return {
      callColor: 'rgba(56, 189, 248, 0.75)',
      callBorder: '#38bdf8',
      putColor: 'rgba(244, 63, 94, 0.75)',
      putBorder: '#f43f5e',
      maxPainLine: '#f59e0b',
      maxPainFill: 'rgba(245, 158, 11, 0.1)',
      maxPainPoint: '#fbbf24',
      ivCallLine: '#38bdf8',
      ivPutLine: '#f43f5e',
      textColor: '#64748b',
      gridColor: 'rgba(255, 255, 255, 0.04)',
      tooltipBg: '#0f172a',
      tooltipTitle: '#f8fafc',
      tooltipBody: '#cbd5e1',
      tooltipBorder: 'rgba(255, 255, 255, 0.1)',
    };
  }
}
window.getThemeColors = getThemeColors;

/**
 * Chart 1: Open Interest Grouped Bars
 */
function buildOiChart(labels, callData, putData, atm) {
  const ctx = document.getElementById('chart-oi');
  if (!ctx) return;

  if (state.charts.oi) state.charts.oi.destroy();
  const theme = getThemeColors();

  state.charts.oi = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Call OI (Resistance)',
          data: callData,
          backgroundColor: theme.callColor,
          borderColor: theme.callBorder,
          borderWidth: 1,
          borderRadius: 4,
        },
        {
          label: 'Put OI (Support)',
          data: putData,
          backgroundColor: theme.putColor,
          borderColor: theme.putBorder,
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
  const theme = getThemeColors();

  state.charts.oiChg = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Call Chg in OI',
          data: callChg,
          backgroundColor: theme.callColor,
          borderRadius: 4,
        },
        {
          label: 'Put Chg in OI',
          data: putChg,
          backgroundColor: theme.putColor,
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
  const theme = getThemeColors();

  state.charts.maxPain = new Chart(ctx, {
    type: 'line',
    data: {
      labels: strikes,
      datasets: [
        {
          label: 'Total Option Writer Payout Loss (INR)',
          data: lossData,
          fill: true,
          borderColor: theme.maxPainLine,
          backgroundColor: theme.maxPainFill,
          borderWidth: 2,
          tension: 0.3,
          pointRadius: strikes.map((s) => (s === maxPainStrike ? 6 : 0)),
          pointBackgroundColor: theme.maxPainPoint,
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
  const theme = getThemeColors();

  state.charts.ivSmile = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Call IV',
          data: ceIv,
          borderColor: theme.ivCallLine,
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 2,
          spanGaps: true,
        },
        {
          label: 'Put IV',
          data: peIv,
          borderColor: theme.ivPutLine,
          borderWidth: 2,
          tension: 0.3,
          pointRadius: 2,
          spanGaps: true,
        },
      ],
    },
    options: getChartOptions('Implied Volatility (IV) Smile & Skew'),
  });
}

/**
 * Standard Adaptive Theme Chart.js Options
 */
function getChartOptions(titleText) {
  const theme = getThemeColors();

  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: theme.textColor,
          font: { family: 'Outfit', size: 12 },
        },
      },
      tooltip: {
        backgroundColor: theme.tooltipBg,
        titleColor: theme.tooltipTitle,
        bodyColor: theme.tooltipBody,
        borderColor: theme.tooltipBorder,
        borderWidth: 1,
        padding: 10,
      },
    },
    scales: {
      x: {
        grid: { color: theme.gridColor },
        ticks: { color: theme.textColor, font: { family: 'JetBrains Mono', size: 10 } },
      },
      y: {
        grid: { color: theme.gridColor },
        ticks: {
          color: theme.textColor,
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
  const statusBadge = document.getElementById('market-badge');
  const statusText = document.getElementById('market-status-text');

  try {
    const res = await fetch('/api/market-status');
    const data = await res.json();

    const capMkt = (data.marketState || []).find((m) => m.market === 'Capital Market');
    const isOpen = capMkt && capMkt.marketStatus && capMkt.marketStatus.toLowerCase() === 'open';

    if (isOpen) {
      if (statusBadge) statusBadge.classList.remove('closed');
      if (statusText) statusText.textContent = 'NSE Market Open';
    } else {
      if (statusBadge) statusBadge.classList.add('closed');
      if (statusText) statusText.textContent = 'NSE Market Closed';
    }
  } catch (e) {
    console.warn('Could not probe market status:', e);
    if (statusBadge) statusBadge.classList.add('closed');
    if (statusText) statusText.textContent = 'NSE Status Unavailable';
  }
}

/**
 * Trigger Data Export
 */
function exportData(format) {
  const params = new URLSearchParams({
    symbol: state.symbol,
    format: format,
    expiry: state.activeExpiry || '',
    equity: state.isEquity ? 'true' : 'false',
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
