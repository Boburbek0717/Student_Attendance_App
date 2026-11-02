/* Read-only refresh: ordinary teacher GET, never a check-in attempt. */
(() => {
  let panel = document.querySelector('#lesson-live');
  const status = document.querySelector('#attendance-sync');
  if (!panel || !status) return;
  let timer, controller, delay = 10000, stopped = false;
  const message = text => { status.textContent = text; };
  const schedule = () => {
    clearTimeout(timer);
    if (!stopped && !document.hidden && navigator.onLine) timer = setTimeout(refresh, delay);
  };
  async function refresh() {
    if (stopped || document.hidden || !navigator.onLine || controller) return;
    // Preserve keyboard focus and don't replace a button while it is being used.
    if (panel.contains(document.activeElement)) {
      message('Updates paused while you use lesson controls. Move focus outside to resume.');
      schedule();
      return;
    }
    controller = new AbortController();
    const timeout = setTimeout(() => controller?.abort(), 8000);
    try {
      const response = await fetch(panel.dataset.url, {cache: 'no-store', signal: controller.signal});
      if (response.redirected || response.status === 401 || response.status === 403) {
        stopped = true;
        message('Your session has ended or access changed. Reload the page to sign in.');
        return;
      }
      if (!response.ok) throw new Error('Refresh unavailable');
      const doc = new DOMParser().parseFromString(await response.text(), 'text/html');
      const next = doc.querySelector('#lesson-live');
      if (!next) throw new Error('Missing lesson');
      if (document.hidden || !navigator.onLine || panel.contains(document.activeElement)) return;
      panel.replaceWith(next);
      panel = next;
      delay = 10000;
      message(`Last updated ${panel.dataset.updated}. Automatic updates every 10 seconds.`);
    } catch (_) {
      if (stopped || document.hidden || !navigator.onLine) return;
      delay = Math.min(delay * 2, 60000);
      message(`Connection interrupted. Displayed attendance may be out of date. Last updated ${panel.dataset.updated}. Retrying when connected.`);
    } finally {
      clearTimeout(timeout);
      controller = null;
      schedule();
    }
  }
  function resume() {
    clearTimeout(timer);
    if (document.hidden || !navigator.onLine) {
      controller?.abort();
      message(`Updates paused${navigator.onLine ? '' : ' — offline'}. Last updated ${panel.dataset.updated}.`);
    } else { delay = 10000; refresh(); }
  }
  document.addEventListener('visibilitychange', resume);
  window.addEventListener('online', resume);
  window.addEventListener('offline', resume);
  window.addEventListener('pagehide', () => { stopped = true; clearTimeout(timer); controller?.abort(); });
  window.addEventListener('pageshow', event => { if (event.persisted) { stopped = false; resume(); } });
  if (document.hidden || !navigator.onLine) resume();
  else {
    message(`Last updated ${panel.dataset.updated}. Automatic updates every 10 seconds.`);
    schedule();
  }
})();
