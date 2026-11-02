/* Local-only offsets: no question text, answers or credentials stored. */
(function () {
    "use strict";
    function normalize(ranges, length) {
        if (!Array.isArray(ranges) || ranges.length > 200) return [];
        const valid = ranges.filter(r => Array.isArray(r) && r.length === 2 &&
            Number.isInteger(r[0]) && Number.isInteger(r[1]) && r[0] >= 0 && r[1] <= length && r[0] < r[1])
            .map(r => r.slice()).sort((a, b) => a[0] - b[0]);
        const result = [];
        for (const range of valid) {
            const last = result[result.length - 1];
            if (last && range[0] <= last[1]) last[1] = Math.max(last[1], range[1]);
            else result.push(range);
        }
        return result;
    }
    function subtract(ranges, start, end) {
        return ranges.flatMap(([a, b]) => {
            if (b <= start || a >= end) return [[a, b]];
            const parts = [];
            if (a < start) parts.push([a, start]);
            if (b > end) parts.push([end, b]);
            return parts;
        });
    }
    if (typeof module !== "undefined" && module.exports) module.exports = {normalize, subtract};
    if (typeof document === "undefined") return;
    const toolbar = document.getElementById("practice-highlights");
    if (!toolbar) return;
    const regions = new Map(Array.from(document.querySelectorAll("[data-highlight-region]:not([data-math-rendered])"), element =>
        [element.dataset.highlightRegion, {element, text: element.textContent, ranges: []}]));
    const key = `sat-factory:highlights:v1:${toolbar.dataset.student}:${toolbar.dataset.revision}`;
    const status = document.getElementById("highlight-status");
    const add = document.getElementById("highlight-add");
    const remove = document.getElementById("highlight-remove");
    const clear = document.getElementById("highlight-clear");
    let pending = null;
    function render() {
        for (const region of regions.values()) {
            const fragment = document.createDocumentFragment();
            let cursor = 0;
            for (const [start, end] of region.ranges) {
                fragment.append(document.createTextNode(region.text.slice(cursor, start)));
                const mark = document.createElement("mark");
                mark.className = "practice-highlight";
                mark.textContent = region.text.slice(start, end);
                fragment.append(mark);
                cursor = end;
            }
            fragment.append(document.createTextNode(region.text.slice(cursor)));
            region.element.replaceChildren(fragment);
        }
        clear.disabled = !Array.from(regions.values()).some(region => region.ranges.length);
    }
    try {
        const stored = JSON.parse(localStorage.getItem(key) || "{}");
        for (const [id, region] of regions) region.ranges = normalize(stored?.[id], region.text.length);
    } catch (_) { /* Unavailable or malformed storage never blocks practice. */ }
    function capture() {
        const selection = window.getSelection();
        if (!selection || selection.isCollapsed || !selection.rangeCount) return;
        pending = null;
        const range = selection.getRangeAt(0);
        for (const [id, region] of regions) {
            if (!region.element.contains(range.startContainer) || !region.element.contains(range.endContainer)) continue;
            const prefix = document.createRange();
            prefix.selectNodeContents(region.element);
            prefix.setEnd(range.startContainer, range.startOffset);
            const start = prefix.toString().length;
            pending = {id, start, end: start + range.toString().length};
            break;
        }
        add.disabled = remove.disabled = !pending;
    }
    function save(message) {
        render();
        pending = null;
        add.disabled = remove.disabled = true;
        window.getSelection()?.removeAllRanges();
        try {
            if (clear.disabled) localStorage.removeItem(key);
            else localStorage.setItem(key, JSON.stringify(Object.fromEntries(
                Array.from(regions, ([id, region]) => [id, region.ranges]))));
            status.textContent = message + " Saved in this browser only.";
        } catch (_) {
            status.textContent = message + " Browser storage is unavailable; these changes last until you leave this page.";
        }
    }
    document.addEventListener("selectionchange", capture);
    // Preserve the selected range when mouse users activate toolbar buttons.
    for (const button of [add, remove]) button.addEventListener("mousedown", event => event.preventDefault());
    add.addEventListener("click", () => {
        if (!pending) return;
        const region = regions.get(pending.id);
        if (region.ranges.length >= 199) {
            status.textContent = "Too many highlights. Clear or remove some before adding more.";
            return;
        }
        region.ranges = normalize([...region.ranges, [pending.start, pending.end]], region.text.length);
        save("Text highlighted.");
    });
    remove.addEventListener("click", () => {
        if (!pending) return;
        const region = regions.get(pending.id);
        const remaining = subtract(region.ranges, pending.start, pending.end);
        if (remaining.length > 200) {
            status.textContent = "Too many separate highlights. Clear some before splitting another.";
            return;
        }
        region.ranges = remaining;
        save("Highlight removed from selection.");
    });
    clear.addEventListener("click", () => {
        for (const region of regions.values()) region.ranges = [];
        save("Highlights cleared.");
    });
    render();
    toolbar.hidden = regions.size === 0;
    if (document.querySelector('[data-highlight-region][data-math-rendered]')) {
        status.textContent = "Highlighting is available in plain-text sections only; formatted equations are excluded.";
    }
})();
