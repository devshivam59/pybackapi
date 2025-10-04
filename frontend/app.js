const state = {
  token: null,
  nextCursor: null,
  lastSearchParams: {},
};

const loginForm = document.getElementById('login-form');
const loginStatus = document.getElementById('login-status');
const importForm = document.getElementById('import-form');
const importStatus = document.getElementById('import-status');
const searchForm = document.getElementById('search-form');
const searchStatus = document.getElementById('search-status');
const resultsMeta = document.getElementById('results-meta');
const resultsTableBody = document.querySelector('#results-table tbody');
const loadMoreButton = document.getElementById('load-more');
const clearDbButton = document.getElementById('clear-db');
const refreshImportsButton = document.getElementById('refresh-imports');
const importsTableBody = document.querySelector('#imports-table tbody');

function setStatus(element, message, tone = 'info') {
  if (!element) return;
  element.textContent = message ?? '';
  element.dataset.tone = tone;
}

function requireToken() {
  if (!state.token) {
    throw new Error('Please login first to obtain an access token.');
  }
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

function renderInstruments(items, { append = false } = {}) {
  if (!append) {
    resultsTableBody.innerHTML = '';
  }
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
      <td>${item.last_price}</td>
    `;
    resultsTableBody.appendChild(row);
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

function formatDate(value) {
  try {
    return new Date(value).toLocaleString();
  } catch (error) {
    return value ?? '';
  }
}

loginForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(loginForm);
  const email = formData.get('email');
  const password = formData.get('password');

  setStatus(loginStatus, 'Logging in…');
  try {
    const response = await fetch(`/v1/auth/login?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`, {
      method: 'POST',
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail ?? 'Login failed');
    }
    const payload = await response.json();
    state.token = payload.access_token;
    setStatus(loginStatus, 'Login successful. Token stored in memory.', 'success');
    await refreshImports();
  } catch (error) {
    console.error(error);
    setStatus(loginStatus, error.message, 'error');
  }
});

importForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    requireToken();
  } catch (error) {
    setStatus(importStatus, error.message, 'error');
    return;
  }

  const source = document.getElementById('import-source').value;
  const replace = document.getElementById('replace-existing').checked;
  const fileInput = document.getElementById('import-file');
  if (!fileInput.files.length) {
    setStatus(importStatus, 'Please choose a CSV file.', 'error');
    return;
  }

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  setStatus(importStatus, 'Uploading file…');
  try {
    const response = await authenticatedFetch(
      `/v1/instruments/import?source=${encodeURIComponent(source)}&replace_existing=${replace}`,
      {
        method: 'POST',
        body: formData,
      },
    );
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail ?? 'Import failed');
    }
    setStatus(importStatus, `Import ${payload.import_id} completed (${payload.rows_ok} rows).`, 'success');
    fileInput.value = '';
    await refreshImports();
  } catch (error) {
    console.error(error);
    setStatus(importStatus, error.message, 'error');
  }
});

async function executeSearch({ append = false, cursor = null } = {}) {
  try {
    requireToken();
  } catch (error) {
    setStatus(searchStatus, error.message, 'error');
    return;
  }

  const params = new URLSearchParams();
  Object.entries(state.lastSearchParams).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, value);
    }
  });
  if (cursor) {
    params.set('cursor', cursor);
  }

  setStatus(searchStatus, append ? 'Loading more…' : 'Searching…');
  try {
    const response = await authenticatedFetch(`/v1/instruments?${params.toString()}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail ?? 'Search failed');
    }
    renderInstruments(payload.items ?? [], { append });
    state.nextCursor = payload.next_cursor ?? null;
    loadMoreButton.disabled = !state.nextCursor;
    const total = payload.total ?? (payload.items?.length ?? 0);
    const displayed = document.querySelectorAll('#results-table tbody tr').length;
    resultsMeta.textContent = `Showing ${displayed} instruments${total ? ` of ${total}` : ''}.`;
    setStatus(searchStatus, payload.items?.length ? `Retrieved ${payload.items.length} instruments.` : 'No instruments found.', 'success');
  } catch (error) {
    console.error(error);
    setStatus(searchStatus, error.message, 'error');
  }
}

searchForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(searchForm);
  state.lastSearchParams = {
    q: formData.get('q')?.trim() ?? '',
    segment: formData.get('segment')?.trim() ?? '',
    exchange: formData.get('exchange')?.trim() ?? '',
    type: formData.get('type')?.trim() ?? '',
    limit: formData.get('limit')?.toString() ?? '20',
  };
  await executeSearch({ append: false });
});

loadMoreButton.addEventListener('click', async () => {
  if (!state.nextCursor) return;
  await executeSearch({ append: true, cursor: state.nextCursor });
});

clearDbButton.addEventListener('click', async () => {
  if (!state.token) {
    setStatus(searchStatus, 'Please login first.', 'error');
    return;
  }
  if (!window.confirm('This will delete all instruments. Continue?')) {
    return;
  }
  setStatus(searchStatus, 'Deleting instrument database…');
  try {
    const response = await authenticatedFetch('/v1/instruments', { method: 'DELETE' });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail ?? 'Failed to delete instruments');
    }
    resultsTableBody.innerHTML = '';
    resultsMeta.textContent = '';
    state.nextCursor = null;
    loadMoreButton.disabled = true;
    setStatus(searchStatus, `Deleted ${payload.deleted ?? 0} instruments.`, 'success');
  } catch (error) {
    console.error(error);
    setStatus(searchStatus, error.message, 'error');
  }
});

async function refreshImports() {
  if (!state.token) {
    return;
  }
  try {
    const response = await authenticatedFetch('/v1/instruments/imports');
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail ?? 'Unable to fetch imports');
    }
    renderImports(payload);
  } catch (error) {
    console.error(error);
    setStatus(importStatus, error.message, 'error');
  }
}

refreshImportsButton.addEventListener('click', refreshImports);

// Provide a starter search on page load for convenience once logged in.
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && state.token && !resultsTableBody.children.length) {
    executeSearch({ append: false });
  }
});
