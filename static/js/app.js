/* ============================================================
   Research Bot Army — Dashboard Application
   Vanilla JS, no dependencies
   ============================================================ */

// ---- State ----
let cfg = null;          // live copy of config.yml as JS object
let pollTimer = null;    // polling timer for active runs
let activeRunId = null;  // currently monitored run

// ---- Utilities ----
const $ = id => document.getElementById(id);
const fmt = {
  dt: s => s ? new Date(s.replace(' ', 'T') + (s.includes('T') ? '' : 'Z')).toLocaleString() : '—',
  dur: (start, end) => {
    if (!start || !end) return '—';
    const s = Math.round((new Date(end) - new Date(start)) / 1000);
    return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`;
  },
  ago: s => {
    if (!s) return '—';
    const diff = Math.round((Date.now() - new Date(s.replace(' ', 'T') + (s.includes('T') ? '' : 'Z'))) / 1000);
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  },
};

function statusBadge(status) {
  const map = {
    completed: ['badge-success', '✓ Completed'],
    running:   ['badge-info',    '⟳ Running'],
    pending:   ['badge-pending', '◌ Pending'],
    failed:    ['badge-danger',  '✕ Failed'],
    success:   ['badge-success', '✓ Success'],
  };
  const [cls, label] = map[status] || ['badge-neutral', status];
  return `<span class="badge ${cls}">${label}</span>`;
}

function eventIcon(type) {
  const m = {
    cycle_started: '🚀', cycle_completed: '✅',
    agent_started: '▶', agent_completed: '✓',
    agent_failed: '✕', synthesis_started: '🤖',
    synthesis_completed: '📋',
  };
  return m[type] || '•';
}

function flash(id, msg, type = 'success') {
  const el = $(id);
  if (!el) return;
  el.textContent = msg;
  el.className = `alert alert-${type} visible`;
  setTimeout(() => { el.classList.remove('visible'); }, 4000);
}

async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const r = await fetch('/api' + path, opts);
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(err.detail || r.statusText);
  }
  return r.json();
}

// ---- Tabs ----
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + target).classList.add('active');
    if (target === 'reports') loadReports();
    if (target === 'runs') loadRuns();
  });
});

// ============================================================
// OVERVIEW TAB
// ============================================================
async function loadOverview() {
  try {
    const status = await api('GET', '/status');
    if (!status.ready) return;

    $('nav-product').textContent = status.product;
    $('stat-product').textContent = status.product;

    const lr = status.last_run;
    if (lr) {
      $('stat-last-run').textContent = fmt.ago(lr.created_at);
      $('stat-last-status').textContent = lr.status;
      $('stat-last-workflow').textContent = lr.workflow || 'Default';
      const dot = $('status-dot');
      dot.className = 'status-dot ' + (lr.status === 'completed' ? 'ok' : lr.status === 'running' ? 'running' : 'error');
    }

    const sched = status.schedule;
    const h = String(sched.hour).padStart(2, '0');
    const m = String(sched.minute).padStart(2, '0');
    $('stat-schedule').textContent = `${h}:${m} UTC daily`;

    $('stat-workflows').textContent = status.enabled_workflows.length + ' active';
    $('stat-wf-names').textContent = status.enabled_workflows.join(', ') || 'None enabled';

    // Populate workflow selector in run panel
    const sel = $('run-workflow-select');
    sel.innerHTML = '<option value="">Default (global agent config)</option>';
    status.enabled_workflows.forEach(wf => {
      const opt = document.createElement('option');
      opt.value = wf; opt.textContent = wf;
      sel.appendChild(opt);
    });

  } catch (e) {
    console.warn('Status load failed:', e);
  }
}

$('btn-run-now').addEventListener('click', async () => {
  const btn = $('btn-run-now');
  const workflow = $('run-workflow-select').value;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Starting…';
  try {
    const res = await api('POST', '/runs', { workflow });
    activeRunId = res.run_id;
    flash('overview-alert', `Run started: ${res.run_id}`, 'info');
    startPolling(res.run_id);
    loadRuns();
  } catch (e) {
    flash('overview-alert', `Error: ${e.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '▶ Run Now';
  }
});

function startPolling(runId) {
  clearInterval(pollTimer);
  const panel = $('active-run-panel');
  const evList = $('active-run-events');
  panel.classList.remove('hidden');
  $('active-run-id').textContent = runId;

  pollTimer = setInterval(async () => {
    try {
      const data = await api('GET', `/runs/${runId}`);
      const run = data.run;
      $('active-run-status').innerHTML = statusBadge(run.status);

      evList.innerHTML = data.events.map(ev => `
        <li class="event-item">
          <span class="event-icon">${eventIcon(ev.event_type)}</span>
          <div class="event-body">
            <span>${ev.agent_name ? `<strong>${ev.agent_name}</strong>: ` : ''}${ev.message || ev.event_type}</span>
            <div class="event-time">${fmt.dt(ev.created_at)}</div>
          </div>
        </li>`).join('');

      if (['completed', 'failed'].includes(run.status)) {
        clearInterval(pollTimer);
        loadOverview();
        loadRuns();
        if (run.status === 'completed') loadReports();
      }
    } catch (e) {
      clearInterval(pollTimer);
    }
  }, 1500);
}

// ============================================================
// CONFIG TAB
// ============================================================
async function loadConfig() {
  try {
    cfg = await api('GET', '/config');
    renderConfig();
  } catch (e) {
    flash('config-alert', `Failed to load config: ${e.message}`, 'error');
  }
}

function renderConfig() {
  if (!cfg) return;
  const p = cfg.product || {};

  $('cfg-product-name').value = p.name || '';
  $('cfg-product-desc').value = p.description || '';
  $('cfg-product-category').value = p.category || '';

  renderTags('cfg-keywords', p.keywords || []);
  renderCompetitors(p.competitors || []);
  renderTags('cfg-subreddits', p.review_subreddits || []);

  const s = cfg.schedule || {};
  $('cfg-sched-hour').value = s.hour ?? 7;
  $('cfg-sched-minute').value = s.minute ?? 0;
  $('cfg-sched-tz').value = s.timezone || 'UTC';
  $('cfg-run-on-start').checked = s.run_on_start !== false;

  const a = cfg.agents || {};
  $('cfg-agent-news').checked = (a.news || {}).enabled !== false;
  $('cfg-agent-competitor').checked = (a.competitor || {}).enabled !== false;
  $('cfg-agent-reviews').checked = (a.reviews || {}).enabled !== false;
  $('cfg-agent-trends').checked = (a.trends || {}).enabled !== false;
  $('cfg-news-max').value = (a.news || {}).max_articles || 15;
  $('cfg-reviews-max').value = (a.reviews || {}).max_posts || 20;
  $('cfg-hn-max').value = (a.trends || {}).hn_stories || 10;
  $('cfg-comp-timeout').value = (a.competitor || {}).timeout_seconds || 25;

  const d = cfg.delivery || {};
  $('cfg-tg-enabled').checked = (d.telegram || {}).enabled || false;
  $('cfg-sl-enabled').checked = (d.slack || {}).enabled || false;
  $('cfg-em-enabled').checked = (d.email || {}).enabled || false;
  $('cfg-em-smtp').value = (d.email || {}).smtp_host || 'smtp.gmail.com';
  $('cfg-em-port').value = (d.email || {}).smtp_port || 587;
  renderTags('cfg-email-to', (d.email || {}).to_addresses || []);

  renderObjectives(cfg.objectives || []);
}

function cfgFromForm() {
  const emailToEl = document.querySelector('#cfg-email-to').closest('.tag-input-wrap');
  const emailTo = Array.from(emailToEl.querySelectorAll('.tag')).map(t => t.dataset.value);

  const keywordsEl = document.querySelector('#cfg-keywords').closest('.tag-input-wrap');
  const keywords = Array.from(keywordsEl.querySelectorAll('.tag')).map(t => t.dataset.value);

  const subredditsEl = document.querySelector('#cfg-subreddits').closest('.tag-input-wrap');
  const subreddits = Array.from(subredditsEl.querySelectorAll('.tag')).map(t => t.dataset.value);

  const objEl = $('objectives-list');
  const objectives = Array.from(objEl.querySelectorAll('.obj-text')).map(el => el.value).filter(Boolean);

  const competitors = [];
  document.querySelectorAll('.comp-row').forEach(row => {
    const name = row.querySelector('.comp-name').value.trim();
    const url = row.querySelector('.comp-url').value.trim();
    if (name || url) competitors.push({ name, url });
  });

  return {
    ...cfg,
    product: {
      ...cfg.product,
      name: $('cfg-product-name').value.trim(),
      description: $('cfg-product-desc').value.trim(),
      category: $('cfg-product-category').value.trim(),
      keywords,
      competitors,
      review_subreddits: subreddits,
    },
    schedule: {
      hour: parseInt($('cfg-sched-hour').value) || 7,
      minute: parseInt($('cfg-sched-minute').value) || 0,
      timezone: $('cfg-sched-tz').value || 'UTC',
      run_on_start: $('cfg-run-on-start').checked,
    },
    agents: {
      news: { enabled: $('cfg-agent-news').checked, max_articles: parseInt($('cfg-news-max').value) || 15 },
      competitor: { enabled: $('cfg-agent-competitor').checked, timeout_seconds: parseInt($('cfg-comp-timeout').value) || 25 },
      reviews: { enabled: $('cfg-agent-reviews').checked, max_posts: parseInt($('cfg-reviews-max').value) || 20 },
      trends: { enabled: $('cfg-agent-trends').checked, hn_stories: parseInt($('cfg-hn-max').value) || 10 },
    },
    delivery: {
      telegram: { enabled: $('cfg-tg-enabled').checked },
      slack: { enabled: $('cfg-sl-enabled').checked },
      email: {
        enabled: $('cfg-em-enabled').checked,
        smtp_host: $('cfg-em-smtp').value.trim(),
        smtp_port: parseInt($('cfg-em-port').value) || 587,
        to_addresses: emailTo,
      },
    },
    objectives,
  };
}

$('btn-save-config').addEventListener('click', async () => {
  const btn = $('btn-save-config');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Saving…';
  try {
    const updated = cfgFromForm();
    await api('PUT', '/config', updated);
    cfg = updated;
    flash('config-alert', 'Config saved! Restart the service to apply schedule changes.', 'success');
  } catch (e) {
    flash('config-alert', `Save failed: ${e.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '💾 Save Config';
  }
});

// ---- Tag Input ----
function renderTags(inputId, values) {
  const input = $(inputId);
  if (!input) return;
  const wrap = input.closest('.tag-input-wrap');
  wrap.querySelectorAll('.tag').forEach(t => t.remove());
  values.forEach(v => {
    if (v) wrap.insertBefore(makeTag(v, inputId), input);
  });
}

function makeTag(value, inputId) {
  const tag = document.createElement('span');
  tag.className = 'tag';
  tag.dataset.value = value;
  tag.innerHTML = `${value}<button type="button" title="Remove">×</button>`;
  tag.querySelector('button').onclick = () => tag.remove();
  return tag;
}

function initTagInput(inputId) {
  const input = $(inputId);
  if (!input) return;
  const wrap = input.closest('.tag-input-wrap');
  wrap.addEventListener('click', () => input.focus());
  input.addEventListener('keydown', e => {
    if ((e.key === 'Enter' || e.key === ',') && input.value.trim()) {
      e.preventDefault();
      const val = input.value.trim().replace(/,$/, '');
      if (val) {
        wrap.insertBefore(makeTag(val, inputId), input);
        input.value = '';
      }
    } else if (e.key === 'Backspace' && !input.value) {
      const tags = wrap.querySelectorAll('.tag');
      if (tags.length) tags[tags.length - 1].remove();
    }
  });
  input.addEventListener('blur', () => {
    const val = input.value.trim().replace(/,$/, '');
    if (val) {
      wrap.insertBefore(makeTag(val, inputId), input);
      input.value = '';
    }
  });
}

// ---- Competitors ----
function renderCompetitors(list) {
  const container = $('competitors-list');
  container.innerHTML = '';
  list.forEach(c => addCompetitorRow(c.name, c.url));
}

function addCompetitorRow(name = '', url = '') {
  const container = $('competitors-list');
  const row = document.createElement('div');
  row.className = 'row-item comp-row';
  row.innerHTML = `
    <input type="text" class="comp-name" placeholder="Competitor name" value="${name}">
    <input type="url" class="comp-url" placeholder="https://competitor.com/pricing" value="${url}" style="flex:2">
    <button class="btn btn-sm btn-danger" onclick="this.closest('.comp-row').remove()" title="Remove">✕</button>
  `;
  container.appendChild(row);
}

$('btn-add-competitor').addEventListener('click', () => addCompetitorRow());

// ---- Objectives ----
function renderObjectives(list) {
  const container = $('objectives-list');
  container.innerHTML = '';
  list.forEach(o => addObjectiveRow(o));
}

function addObjectiveRow(text = '') {
  const container = $('objectives-list');
  const row = document.createElement('div');
  row.className = 'row-item';
  row.innerHTML = `
    <input type="text" class="obj-text" placeholder="e.g. Monitor competitor pricing weekly" value="${text}">
    <button class="btn btn-sm btn-danger" onclick="this.closest('.row-item').remove()" title="Remove">✕</button>
  `;
  container.appendChild(row);
}

$('btn-add-objective').addEventListener('click', () => addObjectiveRow());

// ============================================================
// WORKFLOWS TAB
// ============================================================
async function loadWorkflows() {
  if (!cfg) await loadConfig();
  renderWorkflows();
}

function renderWorkflows() {
  const container = $('workflows-container');
  container.innerHTML = '';
  const workflows = cfg.workflows || [];

  if (workflows.length === 0) {
    container.innerHTML = '<p class="text-muted text-sm">No workflows defined. Add one below.</p>';
  }

  workflows.forEach((wf, i) => {
    container.appendChild(buildWfCard(wf, i));
  });
}

function buildWfCard(wf, idx) {
  const card = document.createElement('div');
  card.className = 'wf-card';
  card.dataset.idx = idx;

  const agentList = ['news', 'competitor', 'reviews', 'trends'];
  const checkedAgents = wf.agents || [];

  const agentCheckboxes = agentList.map(a => {
    const checked = checkedAgents.includes(a);
    const icons = { news: '📰', competitor: '🔍', reviews: '💬', trends: '📈' };
    return `
      <label class="agent-check ${checked ? 'selected' : ''}" data-agent="${a}">
        <input type="checkbox" ${checked ? 'checked' : ''}>
        <span class="agent-icon">${icons[a]}</span>${a}
      </label>`;
  }).join('');

  const objectives = (wf.objectives || []).map((o, i2) =>
    `<div class="row-item">
       <input type="text" class="wf-obj" value="${o}" placeholder="Research objective">
       <button class="btn btn-sm btn-danger" onclick="this.closest('.row-item').remove()">✕</button>
     </div>`
  ).join('');

  card.innerHTML = `
    <div class="wf-header" onclick="toggleWf(this)">
      <label class="toggle" onclick="event.stopPropagation()">
        <input type="checkbox" class="wf-enabled" ${wf.enabled ? 'checked' : ''}>
        <span class="toggle-slider"></span>
      </label>
      <div class="wf-title">${wf.name || 'Unnamed Workflow'}</div>
      <div class="wf-meta">${(wf.agents || []).join(', ')} — ${wf.manager || 'No manager'}</div>
      <span class="wf-chevron">▾</span>
    </div>
    <div class="wf-body">
      <div class="grid-2">
        <div class="form-group">
          <label>Workflow Name</label>
          <input type="text" class="wf-name" value="${wf.name || ''}" placeholder="Daily Market Brief">
        </div>
        <div class="form-group">
          <label>Team Manager / Lead <span class="label-hint">(for context)</span></label>
          <input type="text" class="wf-manager" value="${wf.manager || ''}" placeholder="Market Intelligence Lead">
        </div>
      </div>
      <div class="form-group">
        <label>Description</label>
        <input type="text" class="wf-desc" value="${wf.description || ''}" placeholder="Short description of what this workflow monitors">
      </div>
      <div class="form-group">
        <label>Agents assigned to this workflow</label>
        <div class="agent-grid wf-agents">${agentCheckboxes}</div>
      </div>
      <div class="grid-2">
        <div class="form-group">
          <label>Schedule — Hour (UTC)</label>
          <input type="number" class="wf-hour" min="0" max="23" value="${(wf.schedule || {}).hour ?? 7}">
        </div>
        <div class="form-group">
          <label>Schedule — Minute</label>
          <input type="number" class="wf-minute" min="0" max="59" value="${(wf.schedule || {}).minute ?? 0}">
        </div>
      </div>
      <div class="form-group">
        <label>Max parallel workers <span class="label-hint">(keep ≤ 2 on 1 GB RAM)</span></label>
        <select class="wf-workers">
          <option value="1" ${(wf.max_workers || 2) === 1 ? 'selected' : ''}>1 worker</option>
          <option value="2" ${(wf.max_workers || 2) === 2 ? 'selected' : ''}>2 workers</option>
          <option value="3" ${(wf.max_workers || 2) === 3 ? 'selected' : ''}>3 workers</option>
          <option value="4" ${(wf.max_workers || 2) === 4 ? 'selected' : ''}>4 workers</option>
        </select>
      </div>
      <div class="section-heading">🎯 Workflow Objectives</div>
      <div class="wf-objectives-list">${objectives}</div>
      <button class="btn btn-secondary btn-sm mt-2" onclick="addWfObjective(this)">+ Add Objective</button>
      <div class="card-footer mt-3">
        <button class="btn btn-danger btn-sm" onclick="removeWfCard(this)">🗑 Remove Workflow</button>
        <button class="btn btn-secondary btn-sm ml-auto" onclick="runWorkflow('${wf.name}')">▶ Run Now</button>
      </div>
    </div>
  `;

  // Wire up agent checkboxes
  card.querySelectorAll('.agent-check').forEach(label => {
    const cb = label.querySelector('input');
    cb.addEventListener('change', () => label.classList.toggle('selected', cb.checked));
  });

  return card;
}

function toggleWf(header) {
  const body = header.nextElementSibling;
  header.classList.toggle('open');
  body.classList.toggle('open');
}

function addWfObjective(btn) {
  const list = btn.previousElementSibling;
  const row = document.createElement('div');
  row.className = 'row-item';
  row.innerHTML = `
    <input type="text" class="wf-obj" placeholder="Research objective">
    <button class="btn btn-sm btn-danger" onclick="this.closest('.row-item').remove()">✕</button>
  `;
  list.appendChild(row);
}

function removeWfCard(btn) {
  btn.closest('.wf-card').remove();
}

function runWorkflow(name) {
  // Switch to overview tab and trigger run
  document.querySelector('[data-tab="overview"]').click();
  $('run-workflow-select').value = name;
  $('btn-run-now').click();
}

$('btn-add-workflow').addEventListener('click', () => {
  if (!cfg) return;
  const newWf = {
    name: 'New Workflow',
    description: '',
    agents: ['news', 'competitor'],
    manager: '',
    objectives: [],
    schedule: { hour: 7, minute: 0 },
    max_workers: 2,
    enabled: true,
  };
  if (!cfg.workflows) cfg.workflows = [];
  cfg.workflows.push(newWf);
  const container = $('workflows-container');
  container.appendChild(buildWfCard(newWf, cfg.workflows.length - 1));
});

$('btn-save-workflows').addEventListener('click', async () => {
  const btn = $('btn-save-workflows');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Saving…';

  try {
    // Collect workflows from DOM
    const workflows = [];
    document.querySelectorAll('.wf-card').forEach(card => {
      const agents = Array.from(card.querySelectorAll('.agent-check.selected')).map(l => l.dataset.agent);
      const objectives = Array.from(card.querySelectorAll('.wf-obj')).map(i => i.value.trim()).filter(Boolean);
      workflows.push({
        name: card.querySelector('.wf-name').value.trim(),
        description: card.querySelector('.wf-desc').value.trim(),
        agents,
        manager: card.querySelector('.wf-manager').value.trim(),
        objectives,
        schedule: {
          hour: parseInt(card.querySelector('.wf-hour').value) || 7,
          minute: parseInt(card.querySelector('.wf-minute').value) || 0,
        },
        max_workers: parseInt(card.querySelector('.wf-workers').value) || 2,
        enabled: card.querySelector('.wf-enabled').checked,
      });
    });

    const updated = { ...cfg, workflows };
    await api('PUT', '/config', updated);
    cfg = updated;
    flash('workflows-alert', 'Workflows saved!', 'success');
    loadOverview();
  } catch (e) {
    flash('workflows-alert', `Save failed: ${e.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '💾 Save Workflows';
  }
});

// ============================================================
// RUNS TAB
// ============================================================
async function loadRuns() {
  try {
    const data = await api('GET', '/runs?limit=25');
    const tbody = $('runs-tbody');
    tbody.innerHTML = data.runs.map(r => `
      <tr>
        <td><span class="font-mono text-xs">${r.id}</span></td>
        <td>${r.workflow || '<span class="text-muted">Default</span>'}</td>
        <td>${statusBadge(r.status)}</td>
        <td>${fmt.ago(r.created_at)}</td>
        <td>${fmt.dur(r.started_at, r.completed_at)}</td>
        <td>
          ${r.report_id ? `<a class="btn btn-secondary btn-sm" href="#" onclick="viewReport(${r.report_id}); return false;">View Report</a>` : ''}
          <button class="btn btn-secondary btn-sm" onclick="viewRunDetail('${r.id}')">Detail</button>
        </td>
      </tr>
    `).join('') || '<tr><td colspan="6" class="text-muted">No runs yet.</td></tr>';
  } catch (e) {
    console.warn('Runs load failed:', e);
  }
}

async function viewRunDetail(runId) {
  try {
    const data = await api('GET', `/runs/${runId}`);
    const run = data.run;
    const modal = $('run-detail-modal');
    $('modal-run-id').textContent = run.id;
    $('modal-run-status').innerHTML = statusBadge(run.status);
    $('modal-run-workflow').textContent = run.workflow || 'Default';
    $('modal-run-started').textContent = fmt.dt(run.started_at);
    $('modal-run-completed').textContent = fmt.dt(run.completed_at);
    $('modal-run-events').innerHTML = data.events.map(ev => `
      <li class="event-item">
        <span class="event-icon">${eventIcon(ev.event_type)}</span>
        <div class="event-body">
          ${ev.agent_name ? `<strong>${ev.agent_name}</strong>: ` : ''}${ev.message || ev.event_type}
          <div class="event-time">${fmt.dt(ev.created_at)}</div>
        </div>
      </li>`).join('');
    modal.classList.remove('hidden');
  } catch (e) {
    alert('Failed to load run: ' + e.message);
  }
}

$('modal-close').addEventListener('click', () => {
  $('run-detail-modal').classList.add('hidden');
});

// ============================================================
// REPORTS TAB
// ============================================================
async function loadReports() {
  try {
    const data = await api('GET', '/reports?limit=30');
    const tbody = $('reports-tbody');
    tbody.innerHTML = data.reports.map(r => `
      <tr>
        <td>${fmt.dt(r.created_at)}</td>
        <td>${r.workflow || '<span class="text-muted">Default</span>'}</td>
        <td>${r.token_count || 0}</td>
        <td>
          <div class="report-preview">${(r.preview || '').replace(/[<>]/g, c => c === '<' ? '&lt;' : '&gt;')}</div>
        </td>
        <td><button class="btn btn-secondary btn-sm" onclick="viewReport(${r.id})">Read</button></td>
      </tr>
    `).join('') || '<tr><td colspan="5" class="text-muted">No reports yet. Run a research cycle first.</td></tr>';
  } catch (e) {
    console.warn('Reports load failed:', e);
  }
}

async function viewReport(reportId) {
  // Switch to reports tab
  document.querySelector('[data-tab="reports"]').click();
  try {
    const report = await api('GET', `/reports/${reportId}`);
    const modal = $('report-modal');
    $('modal-report-date').textContent = fmt.dt(report.created_at);
    $('modal-report-workflow').textContent = report.workflow || 'Default';
    $('modal-report-tokens').textContent = report.token_count || 0;
    $('modal-report-content').textContent = report.report_md;
    modal.classList.remove('hidden');
  } catch (e) {
    alert('Failed to load report: ' + e.message);
  }
}

$('report-modal-close').addEventListener('click', () => {
  $('report-modal').classList.add('hidden');
});

$('btn-download-report').addEventListener('click', () => {
  const text = $('modal-report-content').textContent;
  const blob = new Blob([text], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'report.md'; a.click();
  URL.revokeObjectURL(url);
});

// Close modals on backdrop click
['run-detail-modal', 'report-modal'].forEach(id => {
  $(id).addEventListener('click', e => {
    if (e.target === $(id)) $(id).classList.add('hidden');
  });
});

// ============================================================
// INIT
// ============================================================
function init() {
  initTagInput('cfg-keywords');
  initTagInput('cfg-subreddits');
  initTagInput('cfg-email-to');

  loadOverview();
  loadConfig();

  // Refresh overview every 30s
  setInterval(loadOverview, 30000);
}

document.addEventListener('DOMContentLoaded', init);

// ============================================================
// FACTORY VIEW — Mission Control Pipeline + Config Architecture
// ============================================================

// ---- Pixel-art SVG agent sprites (28×40, crispEdges) ----
// Each character has: head, eyes, body with icon, legs
const SPRITES = {
  news: `<svg width="28" height="40" viewBox="0 0 28 40" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">
    <rect x="6" y="0" width="16" height="14" fill="#3b82f6"/>
    <rect x="6" y="0" width="16" height="2"  fill="#2563eb"/>
    <rect x="8" y="3" width="4"  height="4"  fill="#fff"/>
    <rect x="16" y="3" width="4"  height="4"  fill="#fff"/>
    <rect x="9" y="4"  width="2"  height="2"  fill="#1e3a8a"/>
    <rect x="17" y="4"  width="2"  height="2"  fill="#1e3a8a"/>
    <rect x="10" y="10" width="8"  height="2"  fill="#1e40af"/>
    <rect x="2" y="15" width="24" height="16" fill="#2563eb"/>
    <rect x="5" y="17" width="18" height="12" fill="#fff"/>
    <rect x="6" y="18" width="16" height="1"  fill="#93c5fd"/>
    <rect x="6" y="20" width="11" height="1"  fill="#93c5fd"/>
    <rect x="6" y="22" width="13" height="1"  fill="#93c5fd"/>
    <rect x="6" y="24" width="8"  height="1"  fill="#93c5fd"/>
    <rect x="6" y="26" width="14" height="1"  fill="#93c5fd"/>
    <rect x="5" y="32" width="8"  height="8"  fill="#1d4ed8"/>
    <rect x="15" y="32" width="8"  height="8"  fill="#1d4ed8"/>
  </svg>`,

  competitor: `<svg width="28" height="40" viewBox="0 0 28 40" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">
    <rect x="6" y="0" width="16" height="14" fill="#8b5cf6"/>
    <rect x="6" y="0" width="16" height="2"  fill="#7c3aed"/>
    <rect x="8" y="3" width="4"  height="4"  fill="#fff"/>
    <rect x="16" y="3" width="4"  height="4"  fill="#fff"/>
    <rect x="9" y="4"  width="2"  height="2"  fill="#3b0764"/>
    <rect x="17" y="4"  width="2"  height="2"  fill="#3b0764"/>
    <rect x="9" y="10" width="10" height="2"  fill="#6d28d9"/>
    <rect x="4" y="2"  width="3"  height="4"  fill="#a78bfa"/>
    <rect x="21" y="2" width="3"  height="4"  fill="#a78bfa"/>
    <rect x="2" y="15" width="24" height="16" fill="#7c3aed"/>
    <rect x="8" y="17" width="12" height="12" fill="#c4b5fd"/>
    <rect x="10" y="19" width="8"  height="8"  fill="#ddd6fe"/>
    <rect x="12" y="21" width="4"  height="4"  fill="#7c3aed"/>
    <rect x="13" y="23" width="6"  height="1"  fill="#7c3aed"/>
    <rect x="15" y="25" width="6"  height="2"  fill="#7c3aed"/>
    <rect x="5" y="32" width="8"  height="8"  fill="#6d28d9"/>
    <rect x="15" y="32" width="8"  height="8"  fill="#6d28d9"/>
  </svg>`,

  reviews: `<svg width="28" height="40" viewBox="0 0 28 40" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">
    <rect x="6" y="0" width="16" height="14" fill="#22c55e"/>
    <rect x="6" y="0" width="16" height="2"  fill="#16a34a"/>
    <rect x="8" y="3" width="4"  height="4"  fill="#fff"/>
    <rect x="16" y="3" width="4"  height="4"  fill="#fff"/>
    <rect x="9" y="4"  width="2"  height="2"  fill="#14532d"/>
    <rect x="17" y="4"  width="2"  height="2"  fill="#14532d"/>
    <rect x="10" y="10" width="8"  height="2"  fill="#15803d"/>
    <rect x="2" y="15" width="24" height="16" fill="#16a34a"/>
    <rect x="5" y="17" width="18" height="10" fill="#bbf7d0"/>
    <rect x="6" y="18" width="14" height="2"  fill="#22c55e"/>
    <rect x="6" y="21" width="10" height="2"  fill="#22c55e"/>
    <rect x="6" y="24" width="12" height="2"  fill="#22c55e"/>
    <rect x="17" y="27" width="4"  height="4"  fill="#16a34a"/>
    <rect x="5" y="32" width="8"  height="8"  fill="#15803d"/>
    <rect x="15" y="32" width="8"  height="8"  fill="#15803d"/>
  </svg>`,

  trends: `<svg width="28" height="40" viewBox="0 0 28 40" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">
    <rect x="6" y="0" width="16" height="14" fill="#f59e0b"/>
    <rect x="6" y="0" width="16" height="2"  fill="#d97706"/>
    <rect x="8" y="3" width="4"  height="4"  fill="#fff"/>
    <rect x="16" y="3" width="4"  height="4"  fill="#fff"/>
    <rect x="9" y="4"  width="2"  height="2"  fill="#78350f"/>
    <rect x="17" y="4"  width="2"  height="2"  fill="#78350f"/>
    <rect x="9" y="10" width="10" height="2"  fill="#b45309"/>
    <rect x="2" y="15" width="24" height="16" fill="#d97706"/>
    <rect x="5" y="17" width="18" height="12" fill="#fef3c7"/>
    <rect x="6" y="26" width="16" height="1"  fill="#d97706"/>
    <rect x="6" y="25" width="2"  height="2"  fill="#f59e0b"/>
    <rect x="10" y="23" width="2"  height="4"  fill="#f59e0b"/>
    <rect x="14" y="21" width="2"  height="6"  fill="#f59e0b"/>
    <rect x="18" y="19" width="2"  height="8"  fill="#ef4444"/>
    <rect x="5" y="32" width="8"  height="8"  fill="#b45309"/>
    <rect x="15" y="32" width="8"  height="8"  fill="#b45309"/>
  </svg>`,

  _claude: `<svg width="28" height="40" viewBox="0 0 28 40" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">
    <rect x="4" y="0" width="20" height="16" fill="#ec4899"/>
    <rect x="4" y="0" width="20" height="2"  fill="#db2777"/>
    <rect x="0" y="4" width="4"  height="8"  fill="#f9a8d4"/>
    <rect x="24" y="4" width="4"  height="8"  fill="#f9a8d4"/>
    <rect x="7" y="3" width="4"  height="4"  fill="#fff"/>
    <rect x="17" y="3" width="4"  height="4"  fill="#fff"/>
    <rect x="8" y="4"  width="2"  height="2"  fill="#831843"/>
    <rect x="18" y="4"  width="2"  height="2"  fill="#831843"/>
    <rect x="9" y="11" width="10" height="2"  fill="#db2777"/>
    <rect x="7" y="9"  width="2"  height="2"  fill="#fce7f3"/>
    <rect x="19" y="9" width="2"  height="2"  fill="#fce7f3"/>
    <rect x="2" y="17" width="24" height="14" fill="#db2777"/>
    <rect x="5" y="19" width="18" height="10" fill="#fdf2f8"/>
    <rect x="7" y="21" width="4"  height="2"  fill="#ec4899"/>
    <rect x="13" y="21" width="2"  height="2"  fill="#ec4899"/>
    <rect x="17" y="21" width="4"  height="2"  fill="#ec4899"/>
    <rect x="7" y="24" width="14" height="2"  fill="#ec4899"/>
    <rect x="7" y="27" width="8"  height="2"  fill="#ec4899"/>
    <rect x="5" y="32" width="8"  height="8"  fill="#be185d"/>
    <rect x="15" y="32" width="8"  height="8"  fill="#be185d"/>
  </svg>`,
};

const AGENT_META = {
  news:       { label: 'News Agent',       color: '#3b82f6', emoji: '📰' },
  competitor: { label: 'Competitor Agent', color: '#8b5cf6', emoji: '🔍' },
  reviews:    { label: 'Reviews Agent',    color: '#22c55e', emoji: '💬' },
  trends:     { label: 'Trends Agent',     color: '#f59e0b', emoji: '📈' },
  _claude:    { label: 'Claude',           color: '#ec4899', emoji: '🤖' },
};

// ---- Factory state ----
let factoryState = null;
let factoryPollTimer = null;
let factoryAgentStages = {};   // { agentName: stageName }

const STAGE_ORDER = ['ready', 'fetching', 'done', 'synthesizing', 'delivered'];

function agentAnimClass(stage) {
  if (stage === 'fetching' || stage === 'synthesizing') return 'working';
  if (stage === 'done' || stage === 'delivered') return 'done';
  return 'idle';
}

function buildAvatarEl(agentKey, stage) {
  const meta = AGENT_META[agentKey] || { label: agentKey, color: '#94a3b8', emoji: '🤖' };
  const sprite = SPRITES[agentKey] || SPRITES._claude;
  const animCls = agentAnimClass(stage);

  const div = document.createElement('div');
  div.className = 'agent-avatar';
  div.dataset.agent = agentKey;
  div.innerHTML = `
    <span class="avatar-sprite ${animCls}">${sprite}</span>
    <span class="avatar-name" style="color:${meta.color}">${meta.label.replace(' Agent','')}</span>
  `;
  return div;
}

function updateStageCount(stage, count) {
  const el = document.getElementById(`count-${stage}`);
  if (el) el.textContent = count;
}

function clearStageActive() {
  STAGE_ORDER.forEach(s => {
    const el = document.getElementById(`stage-${s}`);
    if (el) el.classList.remove('active');
    const floor = document.getElementById(`floor-${s}`);
    if (floor) floor.classList.remove('scanning');
  });
}

function placeAgentsOnPipeline(agentStages, activeAgentKeys) {
  // Figure out which stage each agent is in
  const stageMap = {};  // stageName → [agentKeys]
  STAGE_ORDER.forEach(s => stageMap[s] = []);

  // All agents start in "ready"
  activeAgentKeys.forEach(k => {
    const stage = agentStages[k] || 'ready';
    stageMap[stage].push(k);
  });

  // Claude is special — only shows up in synthesizing/delivered
  if (agentStages['_claude']) {
    stageMap[agentStages['_claude']].push('_claude');
  }

  clearStageActive();

  // Render each stage floor
  STAGE_ORDER.forEach(stage => {
    const floor = document.getElementById(`floor-${stage}`);
    if (!floor) return;
    const agents = stageMap[stage];

    // Remove agents that are no longer here
    Array.from(floor.querySelectorAll('.agent-avatar')).forEach(el => {
      if (!agents.includes(el.dataset.agent)) el.remove();
    });

    // Add agents now in this stage (if not already present)
    agents.forEach(key => {
      if (!floor.querySelector(`[data-agent="${key}"]`)) {
        floor.appendChild(buildAvatarEl(key, stage));
      } else {
        // Update animation class
        const sprite = floor.querySelector(`[data-agent="${key}"] .avatar-sprite`);
        if (sprite) {
          sprite.className = `avatar-sprite ${agentAnimClass(stage)}`;
        }
      }
    });

    updateStageCount(stage, agents.length);

    // Highlight active stages
    if (agents.length > 0) {
      const stageEl = document.getElementById(`stage-${stage}`);
      if (stageEl) stageEl.classList.add('active');
      if (stage === 'fetching' || stage === 'synthesizing') {
        floor.classList.add('scanning');
      }
    }
  });
}

function eventIconF(type) {
  const m = {
    cycle_started: '🚀', cycle_completed: '✅', agent_started: '▶',
    agent_completed: '✓', agent_failed: '✕', synthesis_started: '🤖',
    synthesis_completed: '📋',
  };
  return m[type] || '•';
}

function renderFactoryEvents(events) {
  const list = $('factory-events');
  if (!events || events.length === 0) {
    list.innerHTML = '<li class="event-item"><div class="event-body text-muted text-sm">Waiting for a run…</div></li>';
    return;
  }
  const recent = events.slice(-10).reverse();
  list.innerHTML = recent.map(ev => `
    <li class="event-item">
      <span class="event-icon">${eventIconF(ev.event_type)}</span>
      <div class="event-body">
        ${ev.agent_name ? `<strong>${ev.agent_name}</strong>: ` : ''}${ev.message || ev.event_type}
        <div class="event-time">${fmt.ago(ev.created_at)}</div>
      </div>
    </li>`).join('');
}

function updateMissionControl(state) {
  const run = state.latest_run;
  $('mc-product').textContent = state.product || '—';
  $('arch-product-name').textContent = state.product || 'Product';

  const dot = $('mc-dot');
  const txt = $('mc-status-text');
  dot.className = 'mc-status-dot';

  if (!run) {
    $('mc-run-id').textContent = '—';
    $('mc-workflow').textContent = 'No runs yet';
    dot.classList.add('idle'); txt.textContent = 'Idle';
    return;
  }

  $('mc-run-id').textContent = run.id;
  $('mc-workflow').textContent = run.workflow || 'Default';

  if (run.status === 'running') {
    dot.classList.add('running'); txt.textContent = 'Running';
  } else if (run.status === 'completed') {
    dot.classList.add('completed'); txt.textContent = 'Completed';
  } else if (run.status === 'failed') {
    dot.classList.add('failed'); txt.textContent = 'Failed';
  } else {
    dot.classList.add('idle'); txt.textContent = run.status;
  }
}

// ---- Workflow Architecture (config.yml reflection) ----
function renderArchitecture(state) {
  const container = $('arch-branches');
  const workflows = state.workflows || [];
  const agentsCfg = state.agents_config || {};

  const agentChip = (key) => {
    const m = AGENT_META[key] || { emoji: '🤖', label: key };
    return `<span class="arch-agent-chip">${m.emoji} ${key}</span>`;
  };

  if (workflows.length === 0) {
    container.innerHTML = '<p class="text-muted text-sm">No workflows defined yet. Add them in the Workflows tab.</p>';
    return;
  }

  container.innerHTML = workflows.map((wf, i) => {
    const isEnabled = wf.enabled;
    const hour = String(wf.schedule?.hour ?? 7).padStart(2, '0');
    const min  = String(wf.schedule?.minute ?? 0).padStart(2, '0');
    const chips = (wf.agents || []).map(agentChip).join('');
    const objs = (wf.objectives || []).map(o =>
      `<div class="arch-obj-item">${o}</div>`
    ).join('');

    return `
      <div class="arch-wf">
        <div class="arch-wf-header">
          <div class="arch-wf-box ${isEnabled ? 'enabled' : 'disabled'}">
            ${isEnabled ? '🔄' : '⏸'} ${wf.name}
            <span class="arch-wf-badge ${isEnabled ? 'on' : 'off'}">${isEnabled ? 'ON' : 'OFF'}</span>
          </div>
        </div>
        <div class="arch-wf-detail">
          <div class="arch-detail-row">
            <span>🤖 Agents:</span>
            <div class="arch-agent-chips">${chips || '<em class="text-muted">none</em>'}</div>
          </div>
          ${wf.manager ? `<div class="arch-detail-row"><span class="arch-manager-text">👤 ${wf.manager}</span></div>` : ''}
          <div class="arch-detail-row">
            <span class="arch-schedule-text">🕐 ${hour}:${min} UTC · ${wf.max_workers || 2} worker${(wf.max_workers || 2) > 1 ? 's' : ''}</span>
          </div>
          ${objs ? `<div class="arch-objectives">${objs}</div>` : ''}
        </div>
      </div>`;
  }).join('');
}

// ---- Determine which agents are assigned to current workflow ----
function getActiveAgentKeys(state) {
  const run = state.latest_run;
  if (!run) {
    // Default to all four in ready state
    return ['news', 'competitor', 'reviews', 'trends'];
  }

  const wfName = run.workflow || '';
  for (const wf of (state.workflows || [])) {
    if (wf.name === wfName) return wf.agents || [];
  }
  // No workflow match — all four
  return ['news', 'competitor', 'reviews', 'trends'];
}

async function loadFactory() {
  try {
    const state = await api('GET', '/factory');
    factoryState = state;

    updateMissionControl(state);
    renderFactoryEvents(state.events);
    renderArchitecture(state);

    const activeKeys = getActiveAgentKeys(state);
    placeAgentsOnPipeline(state.agent_stages || {}, activeKeys);

    // Start polling if a run is active
    const run = state.latest_run;
    if (run && run.status === 'running') {
      startFactoryPoll();
    } else {
      stopFactoryPoll();
    }
  } catch (e) {
    console.warn('Factory load failed:', e);
  }
}

function startFactoryPoll() {
  if (factoryPollTimer) return;
  factoryPollTimer = setInterval(loadFactory, 1800);
}

function stopFactoryPoll() {
  if (factoryPollTimer) {
    clearInterval(factoryPollTimer);
    factoryPollTimer = null;
  }
}

// Hook factory tab into tab switcher
document.querySelectorAll('.tab-btn').forEach(btn => {
  if (btn.dataset.tab === 'factory') {
    btn.addEventListener('click', () => {
      loadFactory();
    });
  }
});
