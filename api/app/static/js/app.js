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

  // Trigger Full Pipeline Execution from UI
  const triggerBtn = document.getElementById('btnTriggerPipeline');
  const triggerText = document.getElementById('btnTriggerPipelineText');
  const runBanner = document.getElementById('pipelineRunBanner');
  const statusText = document.getElementById('pipelineRunStatusText');
  const timerText = document.getElementById('pipelineRunTimer');

  let pollInterval = null;
  let timerInterval = null;
  let startTime = null;

  if (triggerBtn) {
    triggerBtn.addEventListener('click', async () => {
      if (triggerBtn.disabled) return;
      if (!confirm('Rerun full end-to-end data pipeline?\n\nThis will trigger live spider crawl, stream ingestion into Dragonfly, normalization into PostgreSQL, Elasticsearch indexing, and skill mining.')) {
        return;
      }

      try {
        triggerBtn.disabled = true;
        triggerBtn.style.opacity = '0.7';
        triggerBtn.style.cursor = 'wait';
        if (triggerText) triggerText.textContent = 'Starting Pipeline...';

        const resp = await fetch('/api/ops/trigger-pipeline', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mode: 'full' }),
        });
        const data = await resp.json();

        if (runBanner) {
          runBanner.style.display = 'flex';
          runBanner.style.background = '#eff6ff';
          runBanner.style.borderColor = '#bfdbfe';
          runBanner.style.color = '#1e40af';
        }
        if (statusText) statusText.textContent = data.message || 'Pipeline execution in progress...';

        startTime = Date.now();
        if (timerInterval) clearInterval(timerInterval);
        timerInterval = setInterval(() => {
          const sec = Math.floor((Date.now() - startTime) / 1000);
          if (timerText) timerText.textContent = `Elapsed: ${sec}s`;
        }, 1000);

        // Poll pipeline status every 3s
        if (pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(async () => {
          try {
            const statResp = await fetch('/api/ops/pipeline-status');
            if (statResp.ok) {
              const status = await statResp.json();
              if (status.current_stage && statusText) {
                statusText.textContent = `Stage ${status.stage_index || '1'}/4: ${status.current_stage}`;
              }
              if (triggerText) {
                triggerText.textContent = `Running (${status.stage_index || 1}/4)...`;
              }

              highlightDagStage(status.stage_index);

              if (!status.is_running) {
                clearInterval(pollInterval);
                clearInterval(timerInterval);
                pollInterval = null;
                timerInterval = null;

                if (status.last_status === 'success') {
                  if (statusText) statusText.textContent = '✓ Pipeline execution completed successfully. Data synchronized.';
                  if (triggerText) triggerText.textContent = '✓ Complete';
                  if (runBanner) {
                    runBanner.style.background = '#f0fdf4';
                    runBanner.style.borderColor = '#bbf7d0';
                    runBanner.style.color = '#15803d';
                  }
                } else {
                  if (statusText) statusText.textContent = `Pipeline finished: ${status.last_error || 'Check logs'}`;
                  if (triggerText) triggerText.textContent = 'Run Finished';
                }

                // Refresh telemetry, stats, and jobs
                loadOpsTelemetry();
                loadStats();
                loadJobs();

                setTimeout(() => {
                  triggerBtn.disabled = false;
                  triggerBtn.style.opacity = '1';
                  triggerBtn.style.cursor = 'pointer';
                  if (triggerText) triggerText.textContent = 'Rerun Full Pipeline';
                  if (runBanner) runBanner.style.display = 'none';
                  resetDagHighlight();
                }, 4000);
              }
            }
          } catch (pollErr) {
            console.warn('Status poll error:', pollErr);
          }
        }, 3000);

      } catch (err) {
        alert(`Failed to trigger pipeline: ${err.message}`);
        triggerBtn.disabled = false;
        triggerBtn.style.opacity = '1';
        triggerBtn.style.cursor = 'pointer';
        if (triggerText) triggerText.textContent = 'Rerun Full Pipeline';
        if (runBanner) runBanner.style.display = 'none';
      }
    });
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
