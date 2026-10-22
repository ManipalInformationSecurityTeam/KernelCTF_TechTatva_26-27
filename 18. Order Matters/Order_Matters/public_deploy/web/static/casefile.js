(() => {
  const $ = (sel) => document.querySelector(sel);
  const folders = [...document.querySelectorAll('.folder')];
  const modal = $('#evidence-modal');
  const ledger = $('#ledger-list');
  const toast = $('#toast');
  const state = { csrf: '', history: [], boxes: [], busy: false, lastFocus: null };
  let toastTimer = null;
  let currentEntry = null;

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 2200);
  }

  async function api(url, data) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf },
      body: JSON.stringify(data),
      credentials: 'same-origin'
    });
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(payload.error || 'The archive did not accept the request.');
    return payload;
  }

  async function loadState() {
    const res = await fetch('/api/state', { credentials: 'same-origin', cache: 'no-store' });
    if (!res.ok) throw new Error('Unable to open the casefile.');
    const payload = await res.json();
    state.csrf = payload.csrf_token;
    state.history = payload.history || [];
    state.boxes = payload.boxes || [];
    render();
  }

  function setFolderState() {
    const opened = new Map(state.history.map(entry => [entry.box, entry]));
    const full = state.history.length >= 9;
    for (const button of folders) {
      const code = button.dataset.box;
      const entry = opened.get(code);
      button.classList.toggle('is-opened', !!entry);
      button.setAttribute('aria-pressed', entry ? 'true' : 'false');
      const badge = button.querySelector('.folder-state');
      badge.textContent = entry ? 'FILED' : (full ? 'SEALED' : 'SEALED');
      // Opened exhibits remain clickable to reopen their original output. New boxes lock after nine entries.
      button.disabled = !entry && full;
      button.title = entry ? 'Reopen recorded exhibit ' + code : (full ? 'The nine-entry file is closed.' : 'Open exhibit ' + code);
    }
  }

  function renderLedger() {
    ledger.innerHTML = '';
    if (!state.history.length) {
      const empty = document.createElement('div'); empty.className = 'ledger-empty';
      const glyph = document.createElement('span'); glyph.className = 'empty-glyph'; glyph.textContent = '∴';
      const p = document.createElement('p'); p.textContent = 'No exhibits have been entered into the ledger.';
      const small = document.createElement('small'); small.textContent = 'The first record will be preserved here.';
      empty.append(glyph, p, small); ledger.append(empty);
    } else {
      for (const entry of state.history) {
        const row = document.createElement('article'); row.className = 'ledger-entry';
        const num = document.createElement('div'); num.className = 'ledger-entry-number'; num.textContent = String(entry.ordinal).padStart(2, '0');
        const main = document.createElement('div'); main.className = 'ledger-entry-main';
        const open = document.createElement('button'); open.type = 'button';
        const title = document.createElement('strong'); title.textContent = `EXHIBIT ${entry.box} · ${entry.title}`;
        const meta = document.createElement('small'); meta.textContent = 'RECOVERED OBSERVATION · RECORDED';
        open.append(title); open.addEventListener('click', () => openModal(entry)); main.append(open, meta);
        const fragment = document.createElement('code'); fragment.className = 'ledger-entry-code'; fragment.textContent = entry.fragment;
        fragment.title = 'Click to reopen this recorded fragment'; fragment.style.cursor = 'pointer';
        fragment.addEventListener('click', () => openModal(entry));
        row.append(num, main, fragment); ledger.append(row);
      }
    }
    $('#entry-count').textContent = String(state.history.length).padStart(2, '0');
    $('#progress-fill').style.width = `${Math.min(100, state.history.length / 9 * 100)}%`;
    $('#ledger-status-text').textContent = state.history.length === 0 ? 'AWAITING FIRST ENTRY' : state.history.length >= 9 ? 'NINE RECORDS PRESERVED' : `${String(state.history.length).padStart(2, '0')} RECORD${state.history.length === 1 ? '' : 'S'} PRESERVED`;
    $('#copy-bundle').disabled = state.history.length === 0;
    $('#copy-status').textContent = state.history.length ? 'READY FOR OFFLINE RECONSTRUCTION' : 'NO MATERIAL COLLECTED';
  }

  function render() { setFolderState(); renderLedger(); }

  function openModal(entry) {
    currentEntry = entry;
    state.lastFocus = document.activeElement;
    $('#modal-box-stamp').textContent = entry.box;
    $('#modal-heading').textContent = entry.title;
    $('#modal-subtitle').textContent = entry.subtitle || '';
    $('#modal-classification').textContent = (state.boxes.find(b => b.id === entry.box)?.classification || 'ARCHIVE RECORD');
    $('#modal-ordinal').textContent = `RECORD ${String(entry.ordinal).padStart(2, '0')}`;
    $('#modal-observation').textContent = entry.observation;
    $('#modal-fragment').textContent = entry.fragment;
    $('#fragment-copy-status').textContent = 'HEX ENCODING · ' + (entry.fragment.length / 2) + ' BYTES';
    modal.hidden = false;
    document.body.classList.add('modal-open');
    $('#modal-close').focus();
  }

  function closeModal() {
    modal.hidden = true;
    document.body.classList.remove('modal-open');
    if (state.lastFocus && typeof state.lastFocus.focus === 'function') state.lastFocus.focus();
  }

  async function selectBox(box, button) {
    const existing = state.history.find(x => x.box === box);
    if (existing) { openModal(existing); return; }
    if (state.busy) return;
    if (state.history.length >= 9) { showToast('The nine-entry file is closed. Previously selected boxes can still be reopened.'); return; }
    state.busy = true;
    folders.forEach(b => b.classList.toggle('is-loading', b === button));
    try {
      const entry = await api('/api/select', { box });
      // An already recorded exhibit reopens its prior entry without creating a duplicate.
      const prior = state.history.find(x => x.box === entry.box);
      if (!prior) state.history.push(entry);
      render();
      openModal(prior || entry);
    } catch (err) {
      showToast(err.message || 'Could not record this exhibit.');
    } finally {
      state.busy = false;
      folders.forEach(b => b.classList.remove('is-loading'));
    }
  }

  folders.forEach(button => button.addEventListener('click', () => selectBox(button.dataset.box, button)));
  $('#modal-close').addEventListener('click', closeModal);
  modal.addEventListener('click', e => { if (e.target === modal) closeModal(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !modal.hidden) closeModal(); });

  $('#copy-one').addEventListener('click', async () => {
    if (!currentEntry) return;
    try {
      await navigator.clipboard.writeText(currentEntry.fragment);
      $('#fragment-copy-status').textContent = 'BLOCK COPIED';
      showToast('Hex block copied.');
    } catch {
      $('#fragment-copy-status').textContent = 'SELECT AND COPY THE HEX ABOVE';
    }
  });

  $('#copy-bundle').addEventListener('click', async () => {
    const joined = state.history.map(x => x.fragment).join('');
    if (!joined) return;
    try {
      await navigator.clipboard.writeText(joined);
      $('#copy-status').textContent = 'ORDERED HEX COPIED';
      showToast('Collected hex stream copied in acquisition order.');
    } catch {
      const temporary = document.createElement('textarea'); temporary.value = joined;
      temporary.style.position = 'fixed'; temporary.style.opacity = '0'; document.body.append(temporary); temporary.select();
      try { document.execCommand('copy'); $('#copy-status').textContent = 'ORDERED HEX COPIED'; }
      catch { $('#copy-status').textContent = 'COPY UNAVAILABLE — OPEN EACH RECORD'; }
      temporary.remove();
    }
  });


  $('#reset-challenge').addEventListener('click', async () => {
    if (state.busy) return;
    const confirmed = window.confirm(
      'Reset the entire challenge? This permanently clears every recorded exhibit and fragment for this run, then starts from zero. It does not undo one individual selection.'
    );
    if (!confirmed) return;
    state.busy = true;
    const resetButton = $('#reset-challenge');
    resetButton.disabled = true;
    const oldLabel = resetButton.textContent;
    resetButton.textContent = 'RESETTING…';
    try {
      const fresh = await api('/api/reset', {});
      state.csrf = fresh.csrf_token;
      state.history = fresh.history || [];
      state.boxes = fresh.boxes || [];
      currentEntry = null;
      modal.hidden = true;
      document.body.classList.remove('modal-open');
      state.lastFocus = null;
      render();
      showToast('Fresh run started. All previous entries were cleared.');
    } catch (err) {
      showToast(err.message || 'Could not reset the challenge.');
      // Re-sync if a network error happened after the server committed the reset.
      try { await loadState(); } catch (_) { /* the original error is already shown */ }
    } finally {
      state.busy = false;
      resetButton.disabled = false;
      resetButton.textContent = oldLabel;
    }
  });

  loadState().catch(err => showToast(err.message || 'Unable to load casefile.'));
})();
