const {test} = require('node:test');
const assert = require('node:assert/strict');
const {normalize, subtract} = require('../app/static/practice-highlights.js');
test('merges overlapping and adjacent highlights without changing input', () => {
    const input=[[5,8],[1,4],[3,6]];
    assert.deepEqual(normalize(input,10),[[1,8]]);
    assert.deepEqual(input,[[5,8],[1,4],[3,6]]);
});
test('rejects malformed, oversized and out of bounds saved data', () => {
    assert.deepEqual(normalize([[0,2],[-1,3],[4,99],['1',3],[4,4]],10),[[0,2]]);
    assert.deepEqual(normalize({passage:'<script>'},10),[]);
    assert.deepEqual(normalize(Array(201).fill([0,1]),10),[]);
});
test('removing selected text splits marks and preserves unrelated marks', () => {
    assert.deepEqual(subtract([[0,10],[12,15]],3,7),[[0,3],[7,10],[12,15]]);
    assert.deepEqual(subtract([[0,10]],0,10),[]);
    assert.deepEqual(subtract([[0,3]],4,5),[[0,3]]);
});
