const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('app/static/home-motion.js', 'utf8');
function setup(reduced) {
    let observed = 0, animated = 0, cancelled = 0, callback, change;
    const preference = {matches: reduced, addEventListener(_, fn) { change = fn; }};
    const target = {animate() { animated++; return {finished: new Promise(() => {}), cancel() {cancelled++;}}; }};
    class Observer {
        constructor(fn) {callback = fn;}
        observe() {observed++;}
        unobserve() {}
        disconnect() {}
    }
    vm.runInNewContext(source, {
        matchMedia: () => preference, window: {IntersectionObserver: Observer},
        IntersectionObserver: Observer, Element: {prototype: {animate() {}}},
        document: {querySelectorAll: () => [target], addEventListener() {}},
    });
    return {show: () => callback([{target, isIntersecting: true}]),
        reduce: () => {preference.matches = true; change();},
        stats: () => ({observed, animated, cancelled})};
}
test('reduced motion skips all entrance animations', () => {
    const page = setup(true); page.show();
    assert.deepEqual(page.stats(), {observed: 0, animated: 0, cancelled: 0});
});
test('entrance plays once and changing preference cancels active motion', () => {
    const page = setup(false); page.show(); page.show(); page.reduce();
    assert.deepEqual(page.stats(), {observed: 1, animated: 1, cancelled: 1});
});
