const test = require('node:test');
const assert = require('node:assert/strict');
const katex = require('../app/static/vendor/katex-0.18.9/katex.min.js');
const options = {trust:false,strict:'error',throwOnError:false,maxExpand:100,maxSize:10};
test('renders fractions, roots, powers and accessible MathML', () => {
 for (const expression of ['\\frac{3}{4}', '\\sqrt{16}', 'x^2 + 2x + 1', '2x+5=17']) {
  const html = katex.renderToString(expression,options);
  assert.match(html, /<math/);
  assert.doesNotMatch(html, /katex-error/);
 }
});
test('blocks external resources and links in math', () => {
 for (const expression of ['\\includegraphics{https://example.com/track}', '\\href{javascript:alert(1)}{click}']) {
  const html = katex.renderToString(expression,options);
  assert.doesNotMatch(html, /<(?:img|a)\b/);
 }
});
test('malformed math and recursive macros fail safely', () => {
 for (const expression of ['\\frac{', '\\def\\a{\\a}\\a']) {
  assert.match(katex.renderToString(expression,options), /katex-error/);
 }
});
