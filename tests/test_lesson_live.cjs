const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../app/static/lesson-live.js'), 'utf8');

function setup({online = true, hidden = false} = {}) {
  const timers = new Map(), events = {}, calls = [], status = {textContent: ''};
  let id = 0, focused = false, replaced = 0;
  const panel = {dataset: {url: '/teacher/lessons/1', updated: '09:00'},
    contains: () => focused, replaceWith: () => replaced++};
  const document = {hidden, querySelector: s => s === '#lesson-live' ? panel : status,
    addEventListener: (name, fn) => events[name] = fn};
  const navigator = {onLine: online};
  let response = {ok: true, text: async () => ''};
  const context = {document, navigator, AbortController,
    window: {addEventListener: (name, fn) => events[name] = fn},
    // A rejected POST can leave the browser at /close; polling must use data-url.
    location: {pathname: '/teacher/lessons/1/close'},
    setTimeout: (fn, ms) => { timers.set(++id, {fn, ms}); return id; },
    clearTimeout: key => timers.delete(key),
    fetch: async (url, options) => { calls.push({url, options}); if (response instanceof Error) throw response; return response; },
    DOMParser: class { parseFromString() { return {querySelector: () => panel}; } }};
  vm.runInNewContext(source, context);
  return {timers, events, calls, status, document, navigator,
    focus: value => focused = value, response: value => response = value,
    replaced: () => replaced,
    tick: async () => { const [key, timer] = [...timers][0]; timers.delete(key); await timer.fn(); }};
}

test('refresh uses canonical GET, replaces the view and schedules only one poll', async () => {
  const app = setup(); await app.tick();
  assert.equal(app.calls[0].url, '/teacher/lessons/1');
  assert.equal(app.calls[0].options.method, undefined);
  assert.equal(app.calls[0].options.cache, 'no-store');
  assert.equal(app.replaced(), 1); assert.equal(app.timers.size, 1);
});
test('offline and hidden pages make no requests; reconnect resumes', async () => {
  const app = setup({online: false});
  assert.equal(app.timers.size, 0); assert.match(app.status.textContent, /offline/);
  app.navigator.onLine = true; app.events.online();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(app.calls.length, 1);
  app.document.hidden = true; app.events.visibilitychange();
  assert.equal(app.timers.size, 0); assert.match(app.status.textContent, /paused/);
});
test('keyboard interaction preserves controls instead of replacing focused content', async () => {
  const app = setup(); app.focus(true); await app.tick();
  assert.equal(app.calls.length, 0); assert.match(app.status.textContent, /paused/);
  app.focus(false); await app.tick(); assert.equal(app.replaced(), 1);
});
test('connection failures retain old content and back off to at most a minute', async () => {
  const app = setup(); app.response(new Error('Disconnected'));
  for (const delay of [20000, 40000, 60000, 60000]) {
    await app.tick(); assert.equal([...app.timers.values()][0].ms, delay);
  }
  assert.equal(app.replaced(), 0); assert.match(app.status.textContent, /out of date/);
});
test('expired sessions stop polling and ask the teacher to sign in', async () => {
  const app = setup(); app.response({redirected: true}); await app.tick();
  assert.equal(app.timers.size, 0); assert.equal(app.replaced(), 0);
  assert.match(app.status.textContent, /sign in/);
});
