const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('app/static/practice-feedback.js', 'utf8');
function setup(withError) {
    const calls = [], events = {};
    const button = { disabled: false, textContent: 'Check answer →',
        setAttribute: (key, value) => { button[key] = value; },
        removeAttribute: key => { delete button[key]; } };
    const elements = {
        'answer-error': withError ? { focus: () => calls.push('error-focus'), scrollIntoView: () => calls.push('error-scroll') } : null,
        'answer-feedback': withError ? null : { dataset: { fresh: 'true' }, focus: () => calls.push('feedback-focus'), scrollIntoView: () => calls.push('feedback-scroll') },
        'practice-submit': button,
        'practice-answer-form': { checkValidity: () => true, addEventListener: (name, callback) => { events[name] = callback; } }
    };
    vm.runInNewContext(source, { document: { getElementById: id => elements[id] }, window: { addEventListener: (name, callback) => { events[name] = callback; } } });
    return { calls, events, button };
}
test('recoverable error receives focus and submission controls recover on Back', () => {
    const { calls, events, button } = setup(true);
    assert.deepEqual(calls, ['error-focus', 'error-scroll']);
    events.submit();
    assert.equal(button.disabled, true);
    assert.equal(button['aria-busy'], 'true');
    events.pageshow();
    assert.equal(button.disabled, false);
    assert.equal(button['aria-busy'], undefined);
    assert.equal(button.textContent, 'Check answer →');
});
test('saved answer feedback still receives focus', () => {
    assert.deepEqual(setup(false).calls, ['feedback-focus', 'feedback-scroll']);
});
