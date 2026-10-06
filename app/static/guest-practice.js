/* Guest-only progress: never read or write authenticated student records. */
(() => {
    const note = document.getElementById('guest-storage-note');
    if (!note) return;
    const key = 'sat-factory-guest-practice-v1';
    let data;
    try {
        data = JSON.parse(localStorage.getItem(key) || '{}');
        if (!data || typeof data !== 'object' || Array.isArray(data)) data = {};
        if (!data.results || typeof data.results !== 'object' || Array.isArray(data.results)) data.results = {};
        if (!Array.isArray(data.bookmarks)) data.bookmarks = [];
        data.bookmarks = data.bookmarks.filter(x => /^\d+$/.test(x)).slice(-1000);
        const result = document.querySelector('[data-guest-result]');
        if (result) {
            const id = result.dataset.guestResult;
            const previous = data.results[id];
            if (!previous || previous.key !== result.dataset.key) {
                const correct = result.dataset.correct === 'true';
                let state = correct ? (previous || Number(result.dataset.number) > 1 ? 'retried' : 'correct') : 'incorrect';
                if (previous && ['correct', 'retried'].includes(previous.state)) state = previous.state;
                delete data.results[id];
                data.results[id] = {state, key:result.dataset.key};
            }
        }
        data.results = Object.fromEntries(Object.entries(data.results).slice(-2000));
        localStorage.setItem(key, JSON.stringify(data));
    } catch (_) {
        note.textContent = 'Free guest practice. Browser storage is unavailable; progress and bookmarks cannot be saved here.';
        return;
    }
    const symbols = {correct:'✓', retried:'○', incorrect:'×'};
    const labels = {correct:'First-try correct', retried:'Correct after a mistake', incorrect:'Not yet correct'};
    for (const tile of document.querySelectorAll('[data-guest-revision]')) {
        const state = data.results[tile.dataset.guestRevision]?.state;
        if (!Object.hasOwn(symbols, state)) continue;
        const badge = document.createElement('span');
        badge.className = `result-symbol result-${state} tile-result`;
        badge.setAttribute('aria-hidden', 'true');
        badge.textContent = symbols[state];
        tile.append(badge);
        tile.setAttribute('aria-label', tile.getAttribute('aria-label').replace('Not attempted', labels[state]));
        tile.title = tile.title.replace('Not attempted', labels[state]);
    }
    const bookmark = document.querySelector('[data-guest-bookmark]');
    if (bookmark) {
        const id = bookmark.dataset.guestBookmark;
        function refresh() {
            const saved = data.bookmarks.includes(id);
            bookmark.setAttribute('aria-pressed', String(saved));
            bookmark.textContent = saved ? 'Remove bookmark' : 'Bookmark question';
        }
        bookmark.hidden = false;
        refresh();
        bookmark.addEventListener('click', () => {
            data.bookmarks = data.bookmarks.includes(id) ? data.bookmarks.filter(x => x !== id) : [...data.bookmarks, id].slice(-1000);
            try { localStorage.setItem(key, JSON.stringify(data)); refresh(); }
            catch (_) { note.textContent = 'Bookmark could not be saved. Browser storage may be full or disabled.'; }
        });
    }
})();
