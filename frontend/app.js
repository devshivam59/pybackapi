const state = {
  token: null,
  nextCursor: null,
  lastSearchParams: {},
  watchlists: [],
  selectedWatchlistId: null,
  kiteStatus: null,
  activePanel: 'overview',
  dashboard: null,
  users: [],
};

const panelButtons = document.querySelectorAll('[data-panel-target]');
const panels = document.querySelectorAll('.panel');

const loginForm = document.getElementById('login-form');
const loginStatus = document.getElementById('login-status');

const dashboardTotals = document.getElementById('dashboard-totals');
const dashboardStatus = document.getElementById('dashboard-status');
const dashboardKite = document.getElementById('dashboard-kite');
const dashboardImport = document.getElementById('dashboard-import');
const dashboardRefreshButton = document.getElementById('dashboard-refresh');

const importForm = document.getElementById('import-form');
const importStatus = document.getElementById('import-status');
const refreshImportsButton = document.getElementById('refresh-imports');
const importsTableBody = document.querySelector('#imports-table tbody');

const searchForm = document.getElementById('search-form');
const searchStatus = document.getElementById('search-status');
const resultsMeta = document.getElementById('results-meta');
const resultsTableBody = document.querySelector('#results-table tbody');
const loadMoreButton = document.getElementById('load-more');
const clearDbButton = document.getElementById('clear-db');

const kiteForm = document.getElementById('kite-form');
const kiteStatus = document.getElementById('kite-status');
const kiteTestButton = document.getElementById('kite-test');
const kiteClearButton = document.getElementById('kite-clear');

const createWatchlistForm = document.getElementById('create-watchlist-form');
const watchlistSelect = document.getElementById('watchlist-select');
const refreshWatchlistsButton = document.getElementById('refresh-watchlists');
const refreshWatchlistItemsButton = document.getElementById('refresh-watchlist-items');
const watchlistStatus = document.getElementById('watchlist-status');
const watchlistMeta = document.getElementById('watchlist-meta');
const watchlistTableBody = document.querySelector('#watchlist-table tbody');

const userSearchForm = document.getElementById('user-search-form');
const userSearchInput = document.getElementById('user-search');
const refreshUsersButton = document.getElementById('refresh-users');
const usersStatus = document.getElementById('users-status');
const usersTableBody = document.querySelector('#users-table tbody');

function setStatus(element, message, tone = 'info') {
  if (!element) return;
  element.textContent = message ?? '';
  if (message) element.dataset.tone = tone;
  else delete element.dataset.tone;
}

function requireToken() {
  if (!state.token) throw new Error('Please login first to obtain an access token.');
}

async function authenticatedFetch(url, options = {}) {
  requireToken();
  const config = { ...options };
  config.headers = new Headers(options.headers || {});
  if (!config.headers.has('Authorization')) {
    config.headers.set('Authorization', `Bearer ${state.token}`);
  }
  return fetch(url, config);
}

function describeKiteStatus(statusPayload) {
  if (!statusPayload || !statusPayload.configured) return 'No Kite credentials stored.';
  const parts = ['Kite credentials active'];
  if (statusPayload.api_key_last4) parts.push(`API key •••${statusPayload.api_key_last4}`);
  if (statusPayload.access_token_last4) parts.push(`Token •••${statusPayload.access_token_last4}`);
  if (statusPayload.valid_till) parts.push(`valid till ${new Date(statusPayload.valid_till).toLocaleString()}`);
  return parts.join(' · ');
}

function setActivePanel(panelId) {
  if (!panelId) return;
  state.activePanel = panelId;
  panels.forEach((p) => p.classList.toggle('active', p.dataset.panel === panelId));
  panelButtons.forEach((b) => b.classList.toggle('active', b.dataset.panelTarget === panelId));

  if (!state.token) return;

  switch (panelId) {
    case 'overview':
      void loadDashboard({ showToast: false });
      break;
    case 'instruments':
      if (!resultsTableBody.children.length) void executeSearch({ append: false });
      void refreshImports();
      break;
    case 'watchlists':
      void loadWatchlists({ preserveSelection: true });
      break;
    case 'kite':
      void refreshKiteStatus({ showMessage: false });
      break;
    case 'users':
      void loadUsers();
      break;
  }
}

function renderInstruments(items, { append = false } = {}) {
  if (!append) resultsTableBody.innerHTML = '';
  for (const item of items) {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${item.id}</td>
      <td>${item.instrument_token}</td>
      <td>${item.tradingsymbol}</td>
      <td>${item.name ?? ''}</td>
      <td>${item.exchange}</td>
      <td>${item.segment}</td>
      <td>${item.instrument_type}</td>
      <td>${item.lot_size}</td>
      <td>${item.tick_size}</td>
      <td>${item.last_price ?? ''}</td>
      <td class="actions"><button type="button" class="table-action add-to-watchlist" data-instrument="${item.id}">Add</button></td>
    `;
    resultsTableBody.appendChild(row);
  }
  syncAddButtonsState();
}

function syncAddButtonsState() {
  document.querySelectorAll('.add-to-watchlist').forEach((btn) => (btn.disabled = !state.selectedWatchlistId));
}

function formatDate(value) {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value ?? '';
  }
}

async function refreshImports() {
  if (!state.token) return;
  try {
    const res = await authenticatedFetch('/v1/instruments/imports');
    const payload = await res.json();
    if (!res.ok) throw new Error(payload.detail ?? 'Unable to fetch imports');
    renderImports(payload);
  } catch (e) {
    console.error(e);
    setStatus(importStatus, e.message, 'error');
  }
}

function renderImports(items) {
  importsTableBody.innerHTML = '';
  for (const imp of items) {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${imp.id}</td>
      <td>${imp.source}</td>
      <td>${imp.status}</td>
      <td>${imp.rows_in}</td>
      <td>${imp.rows_ok}</td>
      <td>${imp.rows_err}</td>
      <td>${formatDate(imp.started_at)}</td>
      <td>${imp.finished_at ? formatDate(imp.finished_at) : ''}</td>
    `;
    importsTableBody.appendChild(row);
  }
}

loginForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(loginForm);
  const email = fd.get('email');
  const password = fd.get('password');
  setStatus(loginStatus, 'Logging in…');
  try {
    const res = await fetch(`/v1/auth/login?email=${enco
