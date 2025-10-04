const state = {
  token: null,
  nextCursor: null,
  lastSearchParams: {},
  watchlists: [],
  selectedWatchlistId: null,
  kiteStatus: null,
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

function setStatus(element, message, tone = 'info') {
  if (!element) return;
  element.textContent = message ?? '';
  if (message) {
    element.dataset.tone = tone;
  } else {
    delete element.dataset.tone;
  }
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

function describeKiteStatus(statusPayload) {
  if (!statusPayload || !statusPayload.configured) {
    return 'No Kite credentials stored.';
  }
  const parts = ['Kite credentials active'];
  if (statusPayload.api_key_last4) {
    parts.push(`API key •••${statusPayload.api_key_last4}`);
  }
  if (statusPayload.access_token_last4) {
    parts.push(`Token •••${statusPayload.access_token_last4}`);
  }
  if (statusPayload.valid_till) {
    parts.push(`valid till ${new Date(statusPayload.valid_till).toLocaleString()}`);
  }
  return parts.join(' · ');
}

function syncAddButtonsState() {
  document.querySelectorAll('.add-to-watchlist').forEach((button) => {
    button.disabled = !state.selectedWatchlistId;
  });
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
      <td>${item.last_price ?? ''}</td>
      <td class="actions">
        <button type="button" class="table-action add-to-watchlist" data-instrument="${item.id}">
          Add
        </button>
      </td>
    `;
    resultsTableBody.appendChild(row);
  }
  syncAddButtonsState();
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

function renderWatchlistOptions() {
  watchlistSelect.innerHTML = '';
  if (!state.watchlists.length) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = 'No watchlists yet';
    option.disabled = true;
    option.selected = true;
    watchlistSelect.appendChild(option);
    watchlistSelect.disabled = true;
    refreshWatchlistItemsButton.disabled = true;
    syncAddButtonsState();
    return;
  }
  watchlistSelect.disabled = false;
  refreshWatchlistItemsButton.disabled = false;
  for (const watchlist of state.watchlists) {
    const option = document.createElement('option');
    option.value = watchlist.id;
    option.textContent = watchlist.name;
    if (watchlist.id === state.selectedWatchlistId) {
      option.selected = true;
    }
    watchlistSelect.appendChild(option);
  }
  if (!state.selectedWatchlistId && state.watchlists.length) {
    state.selectedWatchlistId = state.watchlists[0].id;
    watchlistSelect.value = state.selectedWatchlistId;
  }
  syncAddButtonsState();
}

function renderWatchlistItems(items) {
  watchlistTableBody.innerHTML = '';
  for (const item of items) {
    const row = document.createElement('tr');
    if (item.missing) {
      row.innerHTML = `
        <td>${item.item_id}</td>
        <td colspan="8">Instrument ${item.instrument_id} missing from catalog.</td>
        <td class="actions">
          <button type="button" class="table-action remove-watchlist-item" data-item="${item.item_id}">
            Remove
          </button>
        </td>
      `;
      watchlistTableBody.appendChild(row);
      continue;
    }
    const updated = item.quote_timestamp ? new Date(item.quote_timestamp).toLocaleString() : '';
    const livePrice = item.live_price != null ? Number(item.live_price).toFixed(2) : '';
    row.innerHTML = `
      <td>${item.item_id}</td>
      <td>${item.instrument_token}</td>
      <td>${item.tradingsymbol}</td>
      <td>${item.name ?? ''}</td>
      <td>${item.exchange}</td>
      <td>${item.instrument_type}</td>
      <td>${livePrice}</td>
      <td>${item.quote_source}</td>
      <td>${updated}</td>
      <td class="actions">
        <button type="button" class="table-action remove-watchlist-item" data-item="${item.item_id}">
          Remove
        </button>
      </td>
    `;
    watchlistTableBody.appendChild(row);
  }
}

function formatDate(value) {
  try {
    return new Date(value).toLocaleString();
  } catch (error) {
    return value ?? '';
  }
}

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

async function refreshKiteStatus({ showMessage = true } = {}) {
  if (!state.token) {
    return;
  }
  try {
    const response = await authenticatedFetch('/v1/admin/brokers/zerodha/token');
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail ?? 'Unable to fetch Kite status');
    }
    state.kiteStatus = payload;
    const message = describeKiteStatus(payload);
    const tone = payload.configured ? 'success' : 'info';
    if (showMessage) {
      setStatus(kiteStatus, message, tone);
    } else {
      kiteStatus.textContent = message;
      kiteStatus.dataset.tone = tone;
    }
  } catch (error) {
    console.error(error);
    setStatus(kiteStatus, error.message, 'error');
  }
}

async function loadWatchlists({ preserveSelection = true } = {}) {
  if (!state.token) {
    return;
  }
  try {
    const response = await authenticatedFetch('/v1/watchlists');
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail ?? 'Unable to fetch watchlists');
    }
    state.watchlists = payload;
    if (!preserveSelection || !state.watchlists.some((w) => w.id === state.selectedWatchlistId)) {
      state.selectedWatchlistId = state.watchlists[0]?.id ?? null;
    }
    renderWatchlistOptions();
    if (state.selectedWatchlistId) {
      await fetchWatchlistItems({ silent: true });
    } else {
      watchlistTableBody.innerHTML = '';
      watchlistMeta.textContent = '';
    }
  } catch (error) {
    console.error(error);
    setStatus(watchlistStatus, error.message, 'error');
  }
}

async function fetchWatchlistItems({ watchlistId = state.selectedWatchlistId, silent = false } = {}) {
  if (!watchlistId) {
    return;
  }
  try {
    requireToken();
  } catch (error) {
    setStatus(watchlistStatus, error.message, 'error');
    return;
  }
  if (!silent) {
    setStatus(watchlistStatus, 'Loading watchlist…');
  }
  try {
    const response = await authenticatedFetch(`/v1/watchlists/${watchlistId}/items`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail ?? 'Unable to load watchlist');
    }
    renderWatchlistItems(payload.items ?? []);
    const count = payload.items?.length ?? 0;
    const refreshedAt = payload.quotes_refreshed_at
      ? new Date(payload.quotes_refreshed_at).toLocaleTimeString()
      : '';
    watchlistMeta.textContent = count
      ? `Loaded ${count} instrument(s). Quotes refreshed at ${refreshedAt}.`
      : 'This watchlist is empty. Search instruments and add them using the actions column.';
    setStatus(watchlistStatus, count ? `Loaded ${count} items.` : 'No instruments in watchlist yet.', 'success');
    if (payload.kite_status) {
      state.kiteStatus = payload.kite_status;
      kiteStatus.textContent = describeKiteStatus(payload.kite_status);
      kiteStatus.dataset.tone = payload.kite_status.configured ? 'success' : 'info';
    }
  } catch (error) {
    console.error(error);
    setStatus(watchlistStatus, error.message, 'error');
  }
}

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
    setStatus(
      searchStatus,
      payload.items?.length ? `Retrieved ${payload.items.length} instruments.` : 'No instruments found.',
      payload.items?.length ? 'success' : 'info',
    );
  } catch (error) {
    console.error(error);
    setStatus(searchStatus, error.message, 'error');
  }
}

async function handleAddToWatchlist(instrumentId) {
  if (!state.selectedWatchlistId) {
    setStatus(watchlistStatus, 'Select or create a watchlist first.', 'error');
    return;
  }
  try {
    requireToken();
  } catch (error) {
    setStatus(watchlistStatus, error.message, 'error');
    return;
  }
  setStatus(watchlistStatus, 'Adding instrument…');
  try {
    const response = await authenticatedFetch(`/v1/watchlists/${state.selectedWatchlistId}/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ instrument_id: instrumentId }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail ?? 'Unable to add instrument');
    }
    setStatus(watchlistStatus, 'Instrument added to watchlist.', 'success');
    await fetchWatchlistItems({ watchlistId: state.selectedWatchlistId, silent: true });
  } catch (error) {
    console.error(error);
    setStatus(watchlistStatus, error.message, 'error');
  }
}

async function handleRemoveWatchlistItem(itemId) {
  if (!state.selectedWatchlistId) {
    return;
  }
  try {
    requireToken();
  } catch (error) {
    setStatus(watchlistStatus, error.message, 'error');
    return;
  }
  setStatus(watchlistStatus, 'Removing instrument…');
  try {
    const response = await authenticatedFetch(`/v1/watchlists/${state.selectedWatchlistId}/items/${itemId}`, {
      method: 'DELETE',
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail ?? 'Unable to remove instrument');
    }
    setStatus(watchlistStatus, payload.detail ?? 'Instrument removed.', 'success');
    await fetchWatchlistItems({ watchlistId: state.selectedWatchlistId, silent: true });
  } catch (error) {
    console.error(error);
    setStatus(watchlistStatus, error.message, 'error');
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
    await refreshKiteStatus({ showMessage: false });
    await loadWatchlists({ preserveSelection: false });
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

refreshImportsButton.addEventListener('click', refreshImports);

kiteForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    requireToken();
  } catch (error) {
    setStatus(kiteStatus, error.message, 'error');
    return;
  }
  const formData = new FormData(kiteForm);
  const apiKey = formData.get('api_key')?.toString().trim() ?? '';
  const accessToken = formData.get('access_token')?.toString().trim() ?? '';
  let validTill = formData.get('valid_till')?.toString().trim() ?? '';
  if (validTill) {
    const parsed = new Date(validTill);
    if (!Number.isNaN(parsed.getTime())) {
      validTill = parsed.toISOString();
    }
  }
  setStatus(kiteStatus, 'Saving Kite credentials…');
  try {
    const response = await authenticatedFetch('/v1/admin/brokers/zerodha/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey, access_token: accessToken, valid_till: validTill || null }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail ?? 'Unable to save credentials');
    }
    setStatus(kiteStatus, payload.detail ?? 'Kite credentials saved.', 'success');
    await refreshKiteStatus({ showMessage: false });
    await fetchWatchlistItems({ silent: true });
  } catch (error) {
    console.error(error);
    setStatus(kiteStatus, error.message, 'error');
  }
});

kiteTestButton?.addEventListener('click', async () => {
  try {
    requireToken();
  } catch (error) {
    setStatus(kiteStatus, error.message, 'error');
    return;
  }
  setStatus(kiteStatus, 'Testing Kite connectivity…');
  try {
    const response = await authenticatedFetch('/v1/admin/brokers/zerodha/test', {
      method: 'POST',
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail ?? 'Kite test failed');
    }
    setStatus(kiteStatus, payload.detail ?? 'Kite connectivity OK.', 'success');
  } catch (error) {
    console.error(error);
    setStatus(kiteStatus, error.message, 'error');
  }
});

kiteClearButton?.addEventListener('click', async () => {
  try {
    requireToken();
  } catch (error) {
    setStatus(kiteStatus, error.message, 'error');
    return;
  }
  if (!window.confirm('Clear stored Kite credentials?')) {
    return;
  }
  setStatus(kiteStatus, 'Clearing Kite credentials…');
  try {
    const response = await authenticatedFetch('/v1/admin/brokers/zerodha/token', {
      method: 'DELETE',
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail ?? 'Unable to clear credentials');
    }
    setStatus(kiteStatus, payload.detail ?? 'Kite credentials cleared.', 'success');
    await refreshKiteStatus({ showMessage: false });
  } catch (error) {
    console.error(error);
    setStatus(kiteStatus, error.message, 'error');
  }
});

createWatchlistForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    requireToken();
  } catch (error) {
    setStatus(watchlistStatus, error.message, 'error');
    return;
  }
  const formData = new FormData(createWatchlistForm);
  const name = formData.get('name')?.toString().trim();
  if (!name) {
    setStatus(watchlistStatus, 'Watchlist name is required.', 'error');
    return;
  }
  setStatus(watchlistStatus, 'Creating watchlist…');
  try {
    const response = await authenticatedFetch('/v1/watchlists', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail ?? 'Unable to create watchlist');
    }
    createWatchlistForm.reset();
    setStatus(watchlistStatus, `Watchlist "${payload.name}" created.`, 'success');
    state.selectedWatchlistId = payload.id;
    await loadWatchlists({ preserveSelection: true });
  } catch (error) {
    console.error(error);
    setStatus(watchlistStatus, error.message, 'error');
  }
});

watchlistSelect?.addEventListener('change', async (event) => {
  state.selectedWatchlistId = event.target.value || null;
  syncAddButtonsState();
  if (state.selectedWatchlistId) {
    await fetchWatchlistItems({ watchlistId: state.selectedWatchlistId });
  } else {
    watchlistTableBody.innerHTML = '';
    watchlistMeta.textContent = '';
  }
});

refreshWatchlistsButton?.addEventListener('click', async () => {
  await loadWatchlists({ preserveSelection: true });
});

refreshWatchlistItemsButton?.addEventListener('click', async () => {
  await fetchWatchlistItems({ watchlistId: state.selectedWatchlistId });
});

resultsTableBody.addEventListener('click', async (event) => {
  const button = event.target.closest('.add-to-watchlist');
  if (!button) return;
  const instrumentId = button.dataset.instrument;
  if (!instrumentId) return;
  await handleAddToWatchlist(instrumentId);
});

watchlistTableBody.addEventListener('click', async (event) => {
  const button = event.target.closest('.remove-watchlist-item');
  if (!button) return;
  const itemId = button.dataset.item;
  if (!itemId) return;
  await handleRemoveWatchlistItem(itemId);
});

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && state.token) {
    if (!resultsTableBody.children.length) {
      executeSearch({ append: false });
    }
    if (state.selectedWatchlistId && !watchlistTableBody.children.length) {
      fetchWatchlistItems({ watchlistId: state.selectedWatchlistId, silent: true });
    }
  }
});

// Prime the UI when already authenticated (e.g., after a refresh with token retained in memory)
if (state.token) {
  refreshImports();
  refreshKiteStatus({ showMessage: false });
  loadWatchlists({ preserveSelection: true });
}
