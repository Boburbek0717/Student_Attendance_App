const {test} = require('node:test');
const assert = require('node:assert/strict');
const {freshState,restoreState,totals,submitAnswer} = require('../scripts/practice_preview/practice.js');
const questions=[{choices:['a','b'],answer:1},{choices:['c','d'],answer:0}];
test('empty submissions and repeated checks never change totals',()=>{
 const s=freshState(2);assert.equal(submitAnswer(s),false);s.selections[0]=1;
 assert.equal(submitAnswer(s),true);assert.equal(submitAnswer(s),false);
 assert.deepEqual(totals(s,questions),{answered:1,correct:1,flagged:0});
});
test('navigation preserves independent answers and review marks',()=>{
 const s=freshState(2);s.selections[0]=0;submitAnswer(s);s.flagged[0]=true;s.index=1;s.selections[1]=0;submitAnswer(s);
 assert.deepEqual(totals(s,questions),{answered:2,correct:1,flagged:1});
 assert.deepEqual(restoreState(JSON.parse(JSON.stringify(s)),questions),s);
});
test('damaged stored selections cannot become submitted results',()=>{
 const s=restoreState({index:999,selections:[-1,42],submitted:[true,true],flagged:[true,'yes']},questions);
 assert.equal(s.index,0);assert.deepEqual(s.submitted,[false,false]);assert.deepEqual(totals(s,questions),{answered:0,correct:0,flagged:1});
 assert.deepEqual(restoreState(null,questions),freshState(2));
});
