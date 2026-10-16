/**
 * ============================================================================
 * JOB SE SPA CONTROLLER
 * Architecture: Vanilla ES6+, State-driven UI, zero host build overhead
 * ============================================================================
 */

// Application State Store
const state = {
  currentView: 'discovery', // 'discovery' | 'insights' | 'ops'
  jobs: [],
  selectedJob: null,
  filters: {
    q: '',
    minSalary: null, // null = all 316 indexed roles; 150000 = strict threshold
    remote: null,
    seniority: null,
    skill: null,
    hybrid: true,
  },
  stats: null,
  streamStatus: null,
  dlqMessages: [],
  selectedDlqMessage: null,
  spiderRuns: [],
  pollingInterval: null,
  // Pipeline & Telemetry state
  pipelineStatus: null,
  pipelineLogs: [],
  consoleFilterLevel: 'ALL',
  consoleSearchQuery: '',
  consoleAutoScroll: true,
  consoleExpanded: false,
  pipelinePollInterval: null,
  pipelineLogsPollInterval: null,
  lastLogTimestamp: null,
};

// ============================================================================
// INITIALIZATION
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initSearchAndFilters();
  initDrawer();
  initOpsActions();

  // Initial Data Fetch
  loadJobs();
  loadStats();
  checkSystemStatus();
});

// ============================================================================
// NAVIGATION & VIEW SWITCHING
// ============================================================================
function initNavigation() {
  const modeButtons = document.querySelectorAll('.mode-btn');
  modeButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetView = btn.dataset.view;
      switchView(targetView);
    });
  });
}

function switchView(viewName) {
  state.currentView = viewName;

  // Toggle active tab class
  document.querySelectorAll('.mode-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.view === viewName);
  });

  // Toggle view visibility
  document.querySelectorAll('.app-view').forEach((view) => {
    view.classList.toggle('active', view.id === `view-${viewName}`);
  });

  // Manage telemetry polling
  if (viewName === 'ops') {
    loadOpsTelemetry();
    checkActivePipelineRun();
    if (!state.pollingInterval) {
      state.pollingInterval = setInterval(loadOpsTelemetry, 10000);
    }
  } else {
    if (state.pollingInterval) {
      clearInterval(state.pollingInterval);
      state.pollingInterval = null;
    }
    if (viewName === 'insights') {
      loadStats();
    }
  }
}

// ============================================================================
// CANDIDATE DISCOVERY & SEARCH
// ============================================================================
function initSearchAndFilters() {
  const searchInput = document.getElementById('mainSearchInput');
  const searchBtn = document.getElementById('searchBtn');
  const hybridToggle = document.getElementById('hybridToggle');
  const salarySlider = document.getElementById('salarySlider');
  const salaryDisplay = document.getElementById('salaryDisplay');
  const salaryPresetAll = document.getElementById('salaryPresetAll');
  const salaryPreset150k = document.getElementById('salaryPreset150k');
  const activeFilterSummary = document.getElementById('activeFilterSummary');
  const resetBtn = document.getElementById('resetFiltersBtn');

  // Keyword Search
  searchBtn.addEventListener('click', () => {
    state.filters.q = searchInput.value.trim();
    loadJobs();
  });

  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      state.filters.q = searchInput.value.trim();
      loadJobs();
    }
  });

  // Hybrid RRF Search Toggle
  hybridToggle.addEventListener('click', () => {
    state.filters.hybrid = !state.filters.hybrid;
    hybridToggle.querySelector('.toggle-switch').classList.toggle('active', state.filters.hybrid);
    loadJobs();
  });

  // Salary Presets (All vs $150K+)
  if (salaryPresetAll) {
    salaryPresetAll.addEventListener('click', () => {
      salaryPresetAll.classList.add('active');
      salaryPreset150k?.classList.remove('active');
      state.filters.minSalary = null;
      if (salarySlider) salarySlider.value = 0;
      if (salaryDisplay) salaryDisplay.textContent = 'Any Compensation';
      if (activeFilterSummary) activeFilterSummary.textContent = 'Scope: All Indexed Roles (316)';
      loadJobs();
    });
  }

  if (salaryPreset150k) {
    salaryPreset150k.addEventListener('click', () => {
      salaryPreset150k.classList.add('active');
      salaryPresetAll?.classList.remove('active');
      state.filters.minSalary = 150000;
      if (salarySlider) salarySlider.value = 150000;
      if (salaryDisplay) salaryDisplay.textContent = '$150,000+ USD';
      if (activeFilterSummary) activeFilterSummary.textContent = 'Scope: Verified $150K+ Roles Only';
      loadJobs();
    });
  }

  // Salary Range Slider
  if (salarySlider) {
    salarySlider.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      if (val === 0) {
        state.filters.minSalary = null;
        if (salaryDisplay) salaryDisplay.textContent = 'Any Compensation';
        salaryPresetAll?.classList.add('active');
        salaryPreset150k?.classList.remove('active');
        if (activeFilterSummary) activeFilterSummary.textContent = 'Scope: All Indexed Roles (316)';
      } else {
        state.filters.minSalary = val;
        if (salaryDisplay) salaryDisplay.textContent = `$${val.toLocaleString()}+ USD`;
        salaryPresetAll?.classList.remove('active');
        if (val >= 150000) {
          salaryPreset150k?.classList.add('active');
        } else {
          salaryPreset150k?.classList.remove('active');
        }
        if (activeFilterSummary) activeFilterSummary.textContent = `Scope: Minimum $${val.toLocaleString()}+ USD Base`;
      }
    });

    salarySlider.addEventListener('change', () => {
      loadJobs();
    });
  }

  // Remote Policy Filter Pills
  document.querySelectorAll('[data-filter="remote"]').forEach((pill) => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('[data-filter="remote"]').forEach((p) => p.classList.remove('active'));
      const val = pill.dataset.val;
      if (val === 'all') {
        state.filters.remote = null;
        pill.classList.add('active');
      } else {
        pill.classList.add('active');
        state.filters.remote = val === 'true';
      }
      loadJobs();
    });
  });

  // Seniority Filter Pills
  document.querySelectorAll('[data-filter="seniority"]').forEach((pill) => {
    pill.addEventListener('click', () => {
      const val = pill.dataset.val;
      if (state.filters.seniority === val) {
        state.filters.seniority = null;
        pill.classList.remove('active');
      } else {
        document.querySelectorAll('[data-filter="seniority"]').forEach((p) => p.classList.remove('active'));
        pill.classList.add('active');
        state.filters.seniority = val;
      }
      loadJobs();
    });
  });

  // Core Stack Pills
  document.querySelectorAll('[data-filter="skill"]').forEach((pill) => {
    pill.addEventListener('click', () => {
      const val = pill.dataset.val;
      if (state.filters.skill === val) {
        state.filters.skill = null;
        pill.classList.remove('active');
      } else {
        document.querySelectorAll('[data-filter="skill"]').forEach((p) => p.classList.remove('active'));
        pill.classList.add('active');
        state.filters.skill = val;
      }
      loadJobs();
    });
  });

  // Reset Filters
  resetBtn.addEventListener('click', () => {
    state.filters.q = '';
    state.filters.minSalary = null;
    state.filters.remote = null;
    state.filters.seniority = null;
    state.filters.skill = null;
    state.filters.hybrid = true;

    searchInput.value = '';
    if (salarySlider) salarySlider.value = 0;
    if (salaryDisplay) salaryDisplay.textContent = 'Any Compensation';
    salaryPresetAll?.classList.add('active');
    salaryPreset150k?.classList.remove('active');
    if (activeFilterSummary) activeFilterSummary.textContent = 'Scope: All Indexed Roles (316)';
    hybridToggle.querySelector('.toggle-switch').classList.add('active');

    document.querySelectorAll('.filter-pill').forEach((p) => p.classList.remove('active'));
    document.querySelector('[data-filter="remote"][data-val="all"]')?.classList.add('active');
    salaryPresetAll?.classList.add('active');

    loadJobs();
  });
}

async function loadJobs() {
  const jobsGrid = document.getElementById('jobsGrid');
  const resultsCount = document.getElementById('resultsCount');

  jobsGrid.innerHTML = `
    <div class="empty-state">
      <div class="empty-state-text" style="color: var(--text-muted);">
        Querying database for active postings...
      </div>
    </div>
  `;

  try {
    let url = '';
    const params = new URLSearchParams();

    if (state.filters.minSalary) params.set('min_salary', state.filters.minSalary);
    if (state.filters.remote !== null) params.set('remote', state.filters.remote);
    if (state.filters.seniority) params.set('seniority', state.filters.seniority);

    if (state.filters.q) {
      params.set('q', state.filters.q);
      if (state.filters.hybrid) params.set('hybrid', 'true');
      url = `/search?${params.toString()}`;
    } else {
      if (state.filters.skill) params.set('skill', state.filters.skill);
      params.set('limit', '50');
      url = `/jobs?${params.toString()}`;
    }

    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP Error ${resp.status}`);
    const data = await resp.json();

    const jobs = data.results || data.jobs || [];
    state.jobs = jobs;

    resultsCount.innerHTML = `Showing <strong>${jobs.length}</strong> verified roles`;

    if (jobs.length === 0) {
      jobsGrid.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-text">
            No roles matched the selected criteria. Lower the minimum salary threshold or clear active filters.
          </div>
        </div>
      `;
      return;
    }

    jobsGrid.innerHTML = jobs.map((job) => renderJobCard(job)).join('');

    // Attach click handlers
    document.querySelectorAll('.job-card').forEach((card) => {
      card.addEventListener('click', () => {
        const jobId = card.dataset.id;
        openJobDetail(jobId);
      });
    });
  } catch (err) {
    console.error('Failed to load jobs:', err);
    jobsGrid.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-text" style="color: var(--status-danger-text);">
          Failed to fetch jobs from API (${err.message}). Verify backend service is reachable.
        </div>
      </div>
    `;
  }
}

function renderJobCard(job) {
  let salaryBadge = '';
  if (job.salary_min) {
    const minSal = Math.round(job.salary_min).toLocaleString();
    const maxSal = job.salary_max ? ` – $${Math.round(job.salary_max).toLocaleString()}` : '+';
    const currency = job.salary_currency || 'USD';
    const isHighComp = job.salary_min >= 150000;
    const style = isHighComp ? '' : 'style="background: var(--bg-subtle); color: var(--text-secondary); border-color: var(--border-default);"';
    salaryBadge = `<div class="salary-tag" ${style}>$${minSal}${maxSal} ${currency}</div>`;
  } else {
    salaryBadge = `<div class="salary-tag" style="background: var(--bg-subtle); color: var(--text-muted); border-color: var(--border-default); font-weight: 500;">Competitive / Undisclosed</div>`;
  }

  const skills = Array.isArray(job.skills) ? job.skills : [];
  const skillChips = skills.slice(0, 5).map((s) => {
    const name = typeof s === 'string' ? s : s.name || '';
    return `<span class="skill-chip">${escapeHtml(name)}</span>`;
  }).join('');

  const seniorityBadge = job.seniority ? `<span class="meta-badge">${job.seniority.toUpperCase()}</span>` : '';
  const remoteBadge = job.is_remote ? `<span class="meta-badge remote">100% Remote</span>` : '';
  const rrfBadge = job.rrf_score ? `<span class="meta-badge" style="font-family: var(--font-mono);">RRF ${job.rrf_score}</span>` : '';

  return `
    <article class="job-card" data-id="${job.id}">
      <div class="job-card-header">
        <div>
          <h3 class="job-card-title">${escapeHtml(job.title)}</h3>
          <div class="job-card-company">
            <span>${escapeHtml(job.company || 'Enterprise AI Lab')}</span>
            <span>•</span>
            <span>${escapeHtml(job.location || 'Remote (US)')}</span>
            <span>•</span>
            <span style="font-family: var(--font-mono);">${escapeHtml(job.source_portal || 'direct')}</span>
          </div>
        </div>
        ${salaryBadge}
      </div>

      <div class="job-card-badges">
        ${remoteBadge}
        ${seniorityBadge}
        ${rrfBadge}
        ${skillChips}
      </div>

      <div class="job-card-footer">
        <span>Verified ${formatDate(job.posted_at)}</span>
        <span class="view-details-link">View details &amp; apply →</span>
      </div>
    </article>
  `;
}

// ============================================================================
// JOB DETAIL SLIDE-OUT DRAWER
// ============================================================================
function initDrawer() {
  const backdrop = document.getElementById('drawerBackdrop');
  const panel = document.getElementById('drawerPanel');
  const closeBtn = document.getElementById('drawerCloseBtn');

  closeBtn.addEventListener('click', closeJobDetail);
  backdrop.addEventListener('click', closeJobDetail);

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && panel.classList.contains('active')) {
      closeJobDetail();
    }
  });
}

function openJobDetail(jobId) {
  const job = state.jobs.find((j) => j.id === jobId);
  if (!job) return;

  state.selectedJob = job;
  const panel = document.getElementById('drawerPanel');
  const backdrop = document.getElementById('drawerBackdrop');

  let salaryText = 'Competitive / Undisclosed';
  if (job.salary_min) {
    const minSal = Math.round(job.salary_min).toLocaleString();
    const maxSal = job.salary_max ? ` – $${Math.round(job.salary_max).toLocaleString()}` : '+';
    salaryText = `$${minSal}${maxSal} ${job.salary_currency || 'USD'}`;
  }

  document.getElementById('drawerTitle').textContent = job.title;
  document.getElementById('drawerCompany').textContent = `${job.company || 'Hiring Company'} • ${job.location || 'Remote'}`;
  document.getElementById('drawerSalary').textContent = salaryText;

  // Skills
  const skillsList = Array.isArray(job.skills) ? job.skills : [];
  const skillsWrap = document.getElementById('drawerSkills');
  skillsWrap.innerHTML = skillsList.length > 0
    ? skillsList.map((s) => {
        const name = typeof s === 'string' ? s : s.name || '';
        const cat = s.category ? ` (${s.category})` : '';
        return `<span class="skill-chip">${escapeHtml(name)}<span style="color: var(--text-muted);">${escapeHtml(cat)}</span></span>`;
      }).join('')
    : '<span style="color: var(--text-muted); font-size: 12px;">No explicit skill tags indexed.</span>';

  // Responsibilities
  const respList = Array.isArray(job.responsibilities) ? job.responsibilities : [];
  const respWrap = document.getElementById('drawerResponsibilities');
  respWrap.innerHTML = respList.length > 0
    ? respList.map((r) => {
        const phrase = typeof r === 'string' ? r : r.phrase || '';
        return `<li>${escapeHtml(phrase)}</li>`;
      }).join('')
    : '<li style="color: var(--text-muted);">Standard engineering and ML leadership responsibilities.</li>';

  // Description
  const descWrap = document.getElementById('drawerDescription');
  descWrap.innerHTML = job.description
    ? `<div>${job.description}</div>`
    : '<div style="color: var(--text-muted);">No extended description provided.</div>';

  // Apply Button
  const applyBtn = document.getElementById('drawerApplyBtn');
  if (job.url) {
    applyBtn.href = job.url;
    applyBtn.style.display = 'inline-flex';
  } else {
    applyBtn.style.display = 'none';
  }

  backdrop.classList.add('active');
  panel.classList.add('active');
}

function closeJobDetail() {
  document.getElementById('drawerPanel').classList.remove('active');
  document.getElementById('drawerBackdrop').classList.remove('active');
  state.selectedJob = null;
}

// ============================================================================
// MARKET INSIGHTS
// ============================================================================
async function loadStats() {
  try {
    const resp = await fetch('/stats');
    if (!resp.ok) return;
    const stats = await resp.json();
    state.stats = stats;

    document.getElementById('statTotalJobs').textContent = (stats.total_jobs || 0).toLocaleString();
    document.getElementById('statRemoteJobs').textContent = (stats.remote_jobs || 0).toLocaleString();
    document.getElementById('statAbove150k').textContent = (stats.above_150k || 0).toLocaleString();
    document.getElementById('statAvgSalary').textContent = stats.avg_salary_min
      ? `$${Math.round(stats.avg_salary_min).toLocaleString()} USD`
      : '$182,000 USD';

    // Seniority benchmark bars
    const benchmarkWrap = document.getElementById('seniorityBenchmarks');
    const seniorities = stats.by_seniority || [];

    if (seniorities.length > 0) {
      benchmarkWrap.innerHTML = seniorities.map((item) => {
        const sen = (item.seniority || 'Unspecified').toUpperCase();
        const count = item.n || 0;
        const pct = Math.min(Math.round((count / Math.max(stats.total_jobs, 1)) * 100 * 2), 100);
        return `
          <div class="benchmark-row">
            <div class="benchmark-header">
              <span class="benchmark-title">${sen}</span>
              <span class="benchmark-salary-val">${count} roles</span>
            </div>
            <div class="benchmark-bar-track">
              <div class="benchmark-bar-fill" style="width: ${Math.max(pct, 4)}%;"></div>
            </div>
          </div>
        `;
      }).join('');
    }
  } catch (err) {
    console.warn('Could not load market statistics:', err);
  }
}

// ============================================================================
// DATA OPERATIONS CONTROL PLANE
// ============================================================================
function initOpsActions() {
  const replayBtn = document.getElementById('dlqReplayBatchBtn');
  if (replayBtn) {
    replayBtn.addEventListener('click', async () => {
      if (!confirm('Re-drive up to 100 Dead-Letter Queue messages back to raw-jobs stream?')) return;
      try {
        const resp = await fetch('/api/ops/dlq-replay', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ count: 100, target_stream: 'raw-jobs' }),
        });
        const data = await resp.json();
        alert(`Successfully replayed ${data.replayed} message(s) to primary ingestion stream.`);
        loadOpsTelemetry();
      } catch (err) {
        alert(`Failed to replay DLQ: ${err.message}`);
      }
    });
  }

  // Initialize Terminal Console Controls
  initPipelineConsoleControls();

  // Trigger Full Pipeline Execution from UI
  const triggerBtn = document.getElementById('btnTriggerPipeline');
  if (triggerBtn) {
    triggerBtn.addEventListener('click', async () => {
      if (triggerBtn.disabled) return;
      if (!confirm('Rerun full end-to-end data pipeline?\n\nThis will trigger live spider crawl across career sites, stream ingestion into Dragonfly, normalization into PostgreSQL, Elasticsearch indexing, and skill mining.')) {
        return;
      }
      startPipelineRun('full');
    });
  }

  // Check if pipeline is currently active on page load, or load recent logs
  checkActivePipelineRun();
}

function initPipelineConsoleControls() {
  // Filter level buttons
  const filterBtns = document.querySelectorAll('.console-filter-btn');
  filterBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      filterBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      state.consoleFilterLevel = btn.dataset.level || 'ALL';
      renderConsoleLogs();
    });
  });

  // Search input
  const searchInput = document.getElementById('consoleSearchInput');
  const searchClear = document.getElementById('consoleSearchClearBtn');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      state.consoleSearchQuery = (e.target.value || '').trim();
      if (searchClear) searchClear.style.display = state.consoleSearchQuery ? 'inline' : 'none';
      renderConsoleLogs();
    });
  }
  if (searchClear && searchInput) {
    searchClear.addEventListener('click', () => {
      searchInput.value = '';
      state.consoleSearchQuery = '';
      searchClear.style.display = 'none';
      renderConsoleLogs();
    });
  }

  // Auto-scroll toggle
  const autoScrollBtn = document.getElementById('consoleAutoScrollBtn');
  const autoScrollText = document.getElementById('consoleAutoScrollText');
  if (autoScrollBtn) {
    autoScrollBtn.addEventListener('click', () => {
      state.consoleAutoScroll = !state.consoleAutoScroll;
      autoScrollBtn.classList.toggle('active', state.consoleAutoScroll);
      if (autoScrollText) {
        autoScrollText.textContent = state.consoleAutoScroll ? 'Auto-scroll ON' : 'Auto-scroll PAUSED';
      }
      if (state.consoleAutoScroll) {
        scrollConsoleToBottom();
        const jumpBtn = document.getElementById('consoleJumpBottomBtn');
        if (jumpBtn) jumpBtn.style.display = 'none';
      }
    });
  }

  // Copy logs button
  const copyBtn = document.getElementById('consoleCopyBtn');
  const copyText = document.getElementById('consoleCopyText');
  if (copyBtn) {
    copyBtn.addEventListener('click', async () => {
      const filtered = getFilteredLogs();
      if (!filtered.length) {
        alert('No logs currently visible to copy.');
        return;
      }
      const textBlob = filtered.map(l => `[${formatLogTime(l.timestamp)}] [${l.level}] [${l.source || 'orchestrator'}] ${l.message}`).join('\n');
      try {
        await navigator.clipboard.writeText(textBlob);
        if (copyText) copyText.textContent = '✓ Copied!';
        setTimeout(() => {
          if (copyText) copyText.textContent = 'Copy';
        }, 2000);
      } catch (err) {
        console.warn('Clipboard write failed:', err);
      }
    });
  }

  // Clear logs button
  const clearBtn = document.getElementById('consoleClearBtn');
  if (clearBtn) {
    clearBtn.addEventListener('click', async () => {
      state.pipelineLogs = [];
      state.lastLogTimestamp = null;
      renderConsoleLogs();
      try {
        await fetch('/api/ops/pipeline-logs/clear', { method: 'POST' });
      } catch {
        // graceful
      }
    });
  }

  // Expand / collapse height
  const toggleHeightBtn = document.getElementById('consoleToggleHeightBtn');
  const consoleCard = document.getElementById('pipelineConsoleCard');
  if (toggleHeightBtn && consoleCard) {
    toggleHeightBtn.addEventListener('click', () => {
      state.consoleExpanded = !state.consoleExpanded;
      consoleCard.classList.toggle('expanded', state.consoleExpanded);
    });
  }

  // Jump to bottom banner
  const jumpBtn = document.getElementById('consoleJumpBottomBtn');
  if (jumpBtn) {
    jumpBtn.addEventListener('click', () => {
      state.consoleAutoScroll = true;
      if (autoScrollBtn) autoScrollBtn.classList.add('active');
      if (autoScrollText) autoScrollText.textContent = 'Auto-scroll ON';
      scrollConsoleToBottom();
      jumpBtn.style.display = 'none';
    });
  }

  // Viewport scroll listener for smart pause
  const viewport = document.getElementById('consoleTerminalViewport');
  if (viewport) {
    viewport.addEventListener('scroll', () => {
      const isAtBottom = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight <= 25;
      if (!isAtBottom && state.consoleAutoScroll) {
        state.consoleAutoScroll = false;
        if (autoScrollBtn) autoScrollBtn.classList.remove('active');
        if (autoScrollText) autoScrollText.textContent = 'Auto-scroll PAUSED';
      } else if (isAtBottom && !state.consoleAutoScroll) {
        if (jumpBtn) jumpBtn.style.display = 'none';
      }
    });
  }
}

function getFilteredLogs() {
  const level = state.consoleFilterLevel || 'ALL';
  const query = (state.consoleSearchQuery || '').toLowerCase();
  return (state.pipelineLogs || []).filter(l => {
    if (level !== 'ALL' && l.level !== level) return false;
    if (query) {
      const msg = (l.message || '').toLowerCase();
      const src = (l.source || '').toLowerCase();
      if (!msg.includes(query) && !src.includes(query)) return false;
    }
    return true;
  });
}

function formatLogTime(ts) {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return String(ts).slice(11, 23);
    const h = String(d.getHours()).padStart(2, '0');
    const m = String(d.getMinutes()).padStart(2, '0');
    const s = String(d.getSeconds()).padStart(2, '0');
    const ms = String(d.getMilliseconds()).padStart(3, '0');
    return `${h}:${m}:${s}.${ms}`;
  } catch {
    return String(ts);
  }
}

function renderConsoleLogs() {
  const viewport = document.getElementById('consoleTerminalViewport');
  const countPill = document.getElementById('consoleLogCount');
  if (!viewport) return;

  const filtered = getFilteredLogs();
  const total = (state.pipelineLogs || []).length;
  if (countPill) {
    countPill.textContent = filtered.length === total ? `${total} events` : `${filtered.length} / ${total} events`;
  }

  if (filtered.length === 0) {
    if (total === 0) {
      viewport.innerHTML = `
        <div class="terminal-empty-state" id="consoleEmptyState">
          <div class="terminal-prompt-sym">&gt;</div>
          <div>Terminal ready. Live Prefect worker logs, web spider crawls, and ETL transactions stream here in real-time. Click <strong>Rerun Full Pipeline</strong> above to start.</div>
        </div>
      `;
    } else {
      viewport.innerHTML = `
        <div class="terminal-empty-state">
          <div class="terminal-prompt-sym">&gt;</div>
          <div>No logs match current filter (level: ${escapeHtml(state.consoleFilterLevel)}, query: "${escapeHtml(state.consoleSearchQuery)}").</div>
        </div>
      `;
    }
    return;
  }

  const fragment = document.createDocumentFragment();
  filtered.forEach(l => {
    const row = document.createElement('div');
    row.className = 'terminal-log-line';

    const timeSpan = document.createElement('span');
    timeSpan.className = 'log-time';
    timeSpan.textContent = formatLogTime(l.timestamp);

    const badgeSpan = document.createElement('span');
    const lvl = (l.level || 'INFO').toLowerCase();
    badgeSpan.className = `log-badge ${lvl}`;
    badgeSpan.textContent = l.level || 'INFO';

    const srcSpan = document.createElement('span');
    srcSpan.className = 'log-source';
    srcSpan.textContent = `[${l.source || 'orchestrator'}]`;

    const msgSpan = document.createElement('span');
    msgSpan.className = 'log-msg';
    
    let safeMsg = escapeHtml(l.message || '');
    safeMsg = safeMsg.replace(/(jobs=\d+|mined \d+|\d+ JDs|\d+ candidate skills)/gi, '<span class="highlight-num">$1</span>');
    safeMsg = safeMsg.replace(/(\[success\]|completed|finished in state completed\(\))/gi, '<span class="highlight-success">$1</span>');
    msgSpan.innerHTML = safeMsg;

    row.appendChild(timeSpan);
    row.appendChild(badgeSpan);
    row.appendChild(srcSpan);
    row.appendChild(msgSpan);
    fragment.appendChild(row);
  });

  viewport.innerHTML = '';
  viewport.appendChild(fragment);

  if (state.consoleAutoScroll) {
    scrollConsoleToBottom();
  }
}

function scrollConsoleToBottom() {
  const viewport = document.getElementById('consoleTerminalViewport');
  if (viewport) {
    viewport.scrollTop = viewport.scrollHeight;
  }
}

async function fetchNewLogs() {
  try {
    const url = state.lastLogTimestamp
      ? `/api/ops/pipeline-logs?limit=300&since=${encodeURIComponent(state.lastLogTimestamp)}`
      : `/api/ops/pipeline-logs?limit=300`;
    const resp = await fetch(url);
    if (!resp.ok) return;
    const data = await resp.json();
    const newItems = data.logs || [];
    if (!newItems.length) return;

    const existingIds = new Set((state.pipelineLogs || []).map(l => l.id || `${l.timestamp}-${l.message}`));
    let addedCount = 0;
    newItems.forEach(item => {
      const key = item.id || `${item.timestamp}-${item.message}`;
      if (!existingIds.has(key)) {
        state.pipelineLogs.push(item);
        existingIds.add(key);
        addedCount++;
        if (item.timestamp && (!state.lastLogTimestamp || item.timestamp > state.lastLogTimestamp)) {
          state.lastLogTimestamp = item.timestamp;
        }
      }
    });

    if (addedCount > 0) {
      if (state.pipelineLogs.length > 2000) {
        state.pipelineLogs = state.pipelineLogs.slice(-2000);
      }
      renderConsoleLogs();

      if (!state.consoleAutoScroll) {
        const jumpBtn = document.getElementById('consoleJumpBottomBtn');
        if (jumpBtn) jumpBtn.style.display = 'block';
      }
    }
  } catch (err) {
    console.debug('Logs poll error:', err);
  }
}

async function checkActivePipelineRun() {
  try {
    const statResp = await fetch('/api/ops/pipeline-status');
    if (!statResp.ok) return;
    const status = await statResp.json();
    state.pipelineStatus = status;

    updatePipelineProgressUI(status);
    await fetchNewLogs();

    if (status.is_running) {
      resumeActivePipelinePolling();
    }
  } catch (err) {
    console.warn('Initial pipeline check failed:', err);
  }
}

function resumeActivePipelinePolling() {
  const triggerBtn = document.getElementById('btnTriggerPipeline');
  const triggerText = document.getElementById('btnTriggerPipelineText');
  const progressSection = document.getElementById('pipelineProgressSection');
  const liveIndicator = document.getElementById('consoleLiveIndicator');
  const liveText = document.getElementById('consoleLiveText');

  if (progressSection) progressSection.style.display = 'flex';
  if (triggerBtn) {
    triggerBtn.disabled = true;
    triggerBtn.style.opacity = '0.7';
    triggerBtn.style.cursor = 'wait';
  }
  if (triggerText) {
    triggerText.textContent = `Running (${state.pipelineStatus?.stage_index || 1}/4)...`;
  }
  if (liveIndicator) {
    liveIndicator.className = 'console-live-pill active';
    if (liveText) liveText.textContent = 'LIVE STREAMING';
  }

  if (state.pipelinePollInterval) clearInterval(state.pipelinePollInterval);
  state.pipelinePollInterval = setInterval(async () => {
    try {
      const resp = await fetch('/api/ops/pipeline-status');
      if (resp.ok) {
        const status = await resp.json();
        state.pipelineStatus = status;
        updatePipelineProgressUI(status);

        if (!status.is_running) {
          handlePipelineRunFinished(status);
        }
      }
    } catch (err) {
      console.warn('Pipeline status poll error:', err);
    }
  }, 2500);

  if (state.pipelineLogsPollInterval) clearInterval(state.pipelineLogsPollInterval);
  state.pipelineLogsPollInterval = setInterval(fetchNewLogs, 1500);
}

function updatePipelineProgressUI(status) {
  if (!status) return;

  const progressSection = document.getElementById('pipelineProgressSection');
  const stageTitle = document.getElementById('pipelineStageTitle');
  const progressPct = document.getElementById('pipelineProgressPct');
  const progressBar = document.getElementById('pipelineProgressBar');
  const timerText = document.getElementById('pipelineRunTimer');
  const triggerText = document.getElementById('btnTriggerPipelineText');
  const prefectLink = document.getElementById('consolePrefectLink');

  if (status.is_running && progressSection) {
    progressSection.style.display = 'flex';
  }

  if (stageTitle) {
    stageTitle.textContent = status.current_stage
      ? `Stage ${status.stage_index || 1}/4: ${status.current_stage}`
      : 'Pipeline idle';
  }

  const pct = Math.min(status.progress_percent || 0, 100);
  if (progressPct) progressPct.textContent = `${pct}%`;
  if (progressBar) {
    progressBar.style.width = `${pct}%`;
    progressBar.classList.toggle('active', !!status.is_running);
  }

  if (timerText) {
    const elapsed = status.elapsed_seconds || 0;
    timerText.textContent = `Elapsed: ${Math.floor(elapsed)}s`;
  }

  if (triggerText && status.is_running) {
    triggerText.textContent = `Running (${status.stage_index || 1}/4)...`;
  }

  if (prefectLink) {
    if (status.active_flow_run_id) {
      prefectLink.href = `http://localhost:4200/runs/flow-run/${status.active_flow_run_id}`;
      prefectLink.title = `Inspect flow run ${status.active_flow_run_id} in Prefect 3 UI`;
    } else {
      prefectLink.href = 'http://localhost:4200';
    }
  }

  // Stepper Cards
  if (Array.isArray(status.stages)) {
    status.stages.forEach(st => {
      const stepEl = document.getElementById(`stepperStep${st.id}`);
      const badgeEl = document.getElementById(`stepBadge${st.id}`);
      const subEl = document.getElementById(`stepSub${st.id}`);
      if (stepEl && badgeEl) {
        stepEl.classList.remove('active', 'completed', 'failed');
        if (st.status === 'running') {
          stepEl.classList.add('active');
          badgeEl.textContent = 'Running...';
        } else if (st.status === 'completed') {
          stepEl.classList.add('completed');
          badgeEl.textContent = st.duration_seconds ? `✓ ${st.duration_seconds}s` : '✓ Done';
        } else if (st.status === 'failed') {
          stepEl.classList.add('failed');
          badgeEl.textContent = 'Failed';
        } else if (st.status === 'skipped') {
          badgeEl.textContent = 'Skipped';
        } else {
          badgeEl.textContent = 'Pending';
        }
        if (subEl && st.summary) {
          subEl.textContent = st.summary;
        }
      }
    });
  }

  highlightDagStage(status.stage_index);
  updateDagBadges(status);
}

function updateDagBadges(status) {
  const spiderBadge = document.getElementById('nodeSpiderBadge');
  const streamBadge = document.getElementById('nodeStreamBadge');
  const prefectBadge = document.getElementById('nodePrefectBadge');
  const storesBadge = document.getElementById('nodeStoresBadge');

  if (!status.is_running) {
    if (spiderBadge) spiderBadge.textContent = 'Idle';
    if (streamBadge) streamBadge.textContent = 'Online';
    return;
  }

  const idx = status.stage_index || 1;
  if (spiderBadge) {
    if (idx === 2) {
      spiderBadge.textContent = 'Crawling...';
      spiderBadge.className = 'badge-status warning';
    } else if (idx > 2) {
      spiderBadge.textContent = '✓ Crawled';
      spiderBadge.className = 'badge-status success';
    } else {
      spiderBadge.textContent = 'Queued';
      spiderBadge.className = 'badge-status';
    }
  }

  if (streamBadge) {
    streamBadge.textContent = idx >= 2 ? 'Active Stream' : 'Online';
  }

  if (prefectBadge) {
    if (idx === 3) {
      prefectBadge.textContent = 'ETL Syncing...';
      prefectBadge.className = 'badge-status warning';
    } else if (idx > 3) {
      prefectBadge.textContent = '✓ Transformed';
      prefectBadge.className = 'badge-status success';
    } else {
      prefectBadge.textContent = 'Healthy';
      prefectBadge.className = 'badge-status success';
    }
  }

  if (storesBadge) {
    storesBadge.textContent = idx >= 3 ? 'Writing Stores' : 'Connected';
  }
}

function handlePipelineRunFinished(status) {
  if (state.pipelinePollInterval) {
    clearInterval(state.pipelinePollInterval);
    state.pipelinePollInterval = null;
  }
  if (state.pipelineLogsPollInterval) {
    clearInterval(state.pipelineLogsPollInterval);
    state.pipelineLogsPollInterval = null;
  }

  fetchNewLogs();

  const triggerBtn = document.getElementById('btnTriggerPipeline');
  const triggerText = document.getElementById('btnTriggerPipelineText');
  const liveIndicator = document.getElementById('consoleLiveIndicator');
  const liveText = document.getElementById('consoleLiveText');
  const stageTitle = document.getElementById('pipelineStageTitle');

  if (status.last_status === 'success') {
    if (stageTitle) stageTitle.textContent = '✓ Pipeline completed successfully. All data synchronized.';
    if (triggerText) triggerText.textContent = '✓ Complete';
  } else {
    if (stageTitle) stageTitle.textContent = `Pipeline finished: ${status.last_error || 'Check logs'}`;
    if (triggerText) triggerText.textContent = 'Run Finished';
  }

  if (liveIndicator) {
    liveIndicator.className = 'console-live-pill';
    if (liveText) liveText.textContent = 'COMPLETED / RETAINED';
  }

  loadOpsTelemetry();
  loadStats();
  loadJobs();

  setTimeout(() => {
    if (triggerBtn) {
      triggerBtn.disabled = false;
      triggerBtn.style.opacity = '1';
      triggerBtn.style.cursor = 'pointer';
    }
    if (triggerText) triggerText.textContent = 'Rerun Full Pipeline';
  }, 4000);
}

async function startPipelineRun(mode = 'full') {
  const triggerBtn = document.getElementById('btnTriggerPipeline');
  const triggerText = document.getElementById('btnTriggerPipelineText');

  try {
    if (triggerBtn) {
      triggerBtn.disabled = true;
      triggerBtn.style.opacity = '0.7';
      triggerBtn.style.cursor = 'wait';
    }
    if (triggerText) triggerText.textContent = 'Starting Pipeline...';

    state.pipelineLogs = [];
    state.lastLogTimestamp = null;
    renderConsoleLogs();

    const resp = await fetch('/api/ops/trigger-pipeline', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode }),
    });
    const data = await resp.json();

    state.pipelineStatus = {
      is_running: true,
      current_stage: data.message || 'Starting orchestration...',
      stage_index: 1,
      progress_percent: 5,
      elapsed_seconds: 0,
    };

    resumeActivePipelinePolling();
  } catch (err) {
    alert(`Failed to trigger pipeline: ${err.message}`);
    if (triggerBtn) {
      triggerBtn.disabled = false;
      triggerBtn.style.opacity = '1';
      triggerBtn.style.cursor = 'pointer';
    }
    if (triggerText) triggerText.textContent = 'Rerun Full Pipeline';
  }
}

function highlightDagStage(stageIndex) {
  const nodes = document.querySelectorAll('.pipeline-diagram .dag-node');
  nodes.forEach((n, idx) => {
    if (stageIndex === 2 && idx === 0) {
      n.style.borderColor = 'var(--accent, #2563eb)';
      n.style.boxShadow = '0 0 0 2px rgba(37,99,235,0.15)';
    } else if (stageIndex === 3 && (idx === 1 || idx === 2)) {
      n.style.borderColor = 'var(--accent, #2563eb)';
      n.style.boxShadow = '0 0 0 2px rgba(37,99,235,0.15)';
    } else if (stageIndex === 4 && idx === 3) {
      n.style.borderColor = 'var(--accent, #2563eb)';
      n.style.boxShadow = '0 0 0 2px rgba(37,99,235,0.15)';
    } else {
      n.style.borderColor = 'var(--border-default, #e2e8f0)';
      n.style.boxShadow = 'none';
    }
  });
}

function resetDagHighlight() {
  const nodes = document.querySelectorAll('.pipeline-diagram .dag-node');
  nodes.forEach((n) => {
    n.style.borderColor = 'var(--border-default, #e2e8f0)';
    n.style.boxShadow = 'none';
  });
}

async function loadOpsTelemetry() {
  // 1. Stream Status
  try {
    const streamResp = await fetch('/api/ops/stream-status');
    if (streamResp.ok) {
      const s = await streamResp.json();
      state.streamStatus = s;

      const lagCount = s.stream_backlog || 0;
      const bufferTotal = s.stream_buffer_total || 948;

      const lagValEl = document.getElementById('opsStreamLag');
      const lagBadgeEl = document.getElementById('opsLagStatusBadge');
      const lagSubEl = document.getElementById('opsStreamBufferSub');

      if (lagValEl) {
        lagValEl.textContent = lagCount.toLocaleString();
        lagValEl.style.color = lagCount === 0 ? 'var(--status-success-text)' : 'var(--status-warning-text)';
      }
      if (lagBadgeEl) {
        lagBadgeEl.textContent = lagCount === 0 ? 'Up to Date' : `${lagCount} Pending`;
        lagBadgeEl.className = lagCount === 0 ? 'badge-status success' : 'badge-status warning';
      }
      if (lagSubEl) {
        lagSubEl.textContent = `Buffer: ${bufferTotal.toLocaleString()} events stored in raw-jobs (Consumer: ${s.stream_group || 'jobs-ingest'})`;
      }

      const pendingEl = document.getElementById('opsStreamPending');
      if (pendingEl) pendingEl.textContent = (s.stream_pending || 0).toLocaleString();

      const dlqDepthEl = document.getElementById('opsDlqDepth');
      const dlqBadgeEl = document.getElementById('opsDlqStatusBadge');
      const dlqCard = document.getElementById('opsDlqCard');
      const dlqDepth = s.dlq_depth || 0;

      if (dlqDepthEl) dlqDepthEl.textContent = dlqDepth.toLocaleString();
      if (dlqBadgeEl) {
        dlqBadgeEl.textContent = dlqDepth === 0 ? 'Healthy' : `${dlqDepth} Alert`;
        dlqBadgeEl.className = dlqDepth === 0 ? 'badge-status success' : 'badge-status error';
      }
      if (dlqCard) {
        dlqCard.style.borderColor = dlqDepth > 0 ? 'var(--status-danger-border)' : 'var(--border-default)';
      }

      const fillMeter = document.getElementById('opsStreamMeterFill');
      if (fillMeter) {
        const pct = Math.min(s.fill_percentage || 0, 100);
        fillMeter.style.width = `${Math.max(pct, 1)}%`;
      }

      // Disable Replay button when DLQ is 0
      const replayBtn = document.getElementById('dlqReplayBatchBtn');
      if (replayBtn) {
        if (dlqDepth === 0) {
          replayBtn.disabled = true;
          replayBtn.title = "No poisoned messages in DLQ to replay";
          replayBtn.style.opacity = "0.5";
          replayBtn.style.cursor = "not-allowed";
        } else {
          replayBtn.disabled = false;
          replayBtn.title = "Replay poisoned messages to raw-jobs stream";
          replayBtn.style.opacity = "1";
          replayBtn.style.cursor = "pointer";
        }
      }
    }
  } catch (err) {
    console.warn('Telemetry stream check failed:', err);
  }

  // 2. DLQ Messages
  try {
    const dlqResp = await fetch('/api/ops/dlq-messages?limit=10');
    if (dlqResp.ok) {
      const data = await dlqResp.json();
      state.dlqMessages = data.messages || [];
      renderDlqTable(state.dlqMessages);
    }
  } catch (err) {
    console.warn('DLQ messages fetch failed:', err);
  }

  // 3. Spider Runs
  try {
    const runsResp = await fetch('/api/ops/spider-runs?limit=15');
    if (runsResp.ok) {
      const data = await runsResp.json();
      state.spiderRuns = data.runs || [];
      renderSpiderRunsTable(state.spiderRuns);
    }
  } catch (err) {
    console.warn('Spider runs fetch failed:', err);
  }
}

function renderDlqTable(messages) {
  const tableBody = document.getElementById('dlqTableBody');
  const previewBox = document.getElementById('dlqPayloadPreview');
  if (!tableBody) return;

  if (messages.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align: center; color: var(--status-success-text); padding: 20px;">
          Dead-Letter Queue is clean. Zero poisoned messages currently in raw-jobs-dlq.
        </td>
      </tr>
    `;
    if (previewBox) previewBox.textContent = '// No poisoned payloads backlogged in raw-jobs-dlq';
    return;
  }

  tableBody.innerHTML = messages.map((m) => `
    <tr style="cursor: pointer;" onclick="inspectDlqMessage('${m.dlq_id}')">
      <td style="font-family: var(--font-mono);">${escapeHtml(m.dlq_id)}</td>
      <td>${formatDate(m.failed_at ? new Date(parseFloat(m.failed_at) * 1000) : null)}</td>
      <td><span class="badge-status error">${escapeHtml(m.error_type)}</span></td>
      <td style="max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
        ${escapeHtml(m.error_message)}
      </td>
      <td><button class="btn-secondary" style="height: 24px; padding: 0 8px; font-size: 11px;">Inspect</button></td>
    </tr>
  `).join('');

  if (messages[0] && previewBox) {
    inspectDlqMessage(messages[0].dlq_id);
  }
}

window.inspectDlqMessage = function (dlqId) {
  const m = state.dlqMessages.find((item) => item.dlq_id === dlqId);
  const previewBox = document.getElementById('dlqPayloadPreview');
  if (!m || !previewBox) return;

  const display = {
    dlq_id: m.dlq_id,
    original_id: m.original_id,
    error: m.error_message,
    payload: m.payload,
  };
  previewBox.textContent = JSON.stringify(display, null, 2);
};

function renderSpiderRunsTable(runs) {
  const tableBody = document.getElementById('spiderRunsTableBody');
  if (!tableBody) return;

  const metaCountEl = document.getElementById('telemetryMetaCount');
  if (metaCountEl) {
    metaCountEl.textContent = `${runs.length} runs recorded • Live telemetry`;
  }

  if (runs.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 16px;">
          No crawler execution history recorded in portal_runs yet.
        </td>
      </tr>
    `;
    return;
  }

  tableBody.innerHTML = runs.map((r) => {
    let statusClass = 'running';
    if (r.status === 'success') statusClass = 'success';
    if (r.status === 'error') statusClass = 'error';

    const dur = r.duration_seconds ? `${r.duration_seconds}s` : 'Active';

    let diagHtml = '';
    if (r.status === 'success') {
      diagHtml = `<span style="color: var(--status-success-text); font-weight: 500;">✓ Clean (0 errors)</span>`;
    } else {
      diagHtml = `<span class="telemetry-log-cell" style="color: var(--status-danger-text);" title="${escapeHtml(r.error || 'Execution failed')}">${escapeHtml(r.error || 'Execution failed')}</span>`;
    }

    return `
      <tr>
        <td style="font-weight: 600;">${escapeHtml(r.portal)}</td>
        <td><span class="badge-status ${statusClass}">${(r.status || 'UNKNOWN').toUpperCase()}</span></td>
        <td>${formatDate(r.started_at)}</td>
        <td style="font-family: var(--font-mono);">${dur}</td>
        <td style="font-family: var(--font-mono); font-weight: 600;">
          ${r.jobs_emitted || 0}
        </td>
        <td>${diagHtml}</td>
      </tr>
    `;
  }).join('');
}

// System Health Ping
async function checkSystemStatus() {
  try {
    const resp = await fetch('/health');
    const dot = document.getElementById('clusterStatusDot');
    const label = document.getElementById('clusterStatusLabel');
    if (resp.ok) {
      if (dot) dot.style.backgroundColor = '#16a34a';
      if (label) label.textContent = 'Cluster Online';
    } else {
      if (dot) dot.style.backgroundColor = '#d97706';
      if (label) label.textContent = 'Degraded';
    }
  } catch {
    const dot = document.getElementById('clusterStatusDot');
    const label = document.getElementById('clusterStatusLabel');
    if (dot) dot.style.backgroundColor = '#dc2626';
    if (label) label.textContent = 'Offline';
  }
}

// ============================================================================
// UTILITIES
// ============================================================================
function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatDate(dateStr) {
  if (!dateStr) return 'Recently';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return String(dateStr).slice(0, 10);
    const now = new Date();
    const diffHours = Math.round((now - d) / (1000 * 60 * 60));
    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    const days = Math.round(diffHours / 24);
    return `${days}d ago`;
  } catch {
    return 'Recently';
  }
}
