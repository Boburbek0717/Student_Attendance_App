const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const code = fs.readFileSync('app/static/guest-practice.js','utf8');
function run(previous, result, blocked=false) {
    let stored = JSON.stringify(previous || {});
    const note={textContent:''};
    vm.runInNewContext(code,{
        document:{getElementById:()=>note,querySelector:s=>s==='[data-guest-result]' && result ? {dataset:result} : null,querySelectorAll:()=>[]},
        localStorage:{getItem:()=>{if(blocked)throw Error();return stored;},setItem:(_,v)=>{stored=v;}}
    });
    return {data:JSON.parse(stored),note:note.textContent};
}
const result=(correct,key='a',number='1')=>({guestResult:'5',correct:String(correct),key,number});
test('guest results distinguish first success from success after error',()=>{
 const first=run(null,result(true)).data;
 assert.equal(first.results['5'].state,'correct');
 const wrong=run(null,result(false)).data;
 assert.equal(wrong.results['5'].state,'incorrect');
 assert.equal(run(wrong,result(true,'b','2')).data.results['5'].state,'retried');
});
test('refresh does not turn first-try correct into retried',()=>{
 const first=run(null,result(true)).data;
 assert.equal(run(first,result(true)).data.results['5'].state,'correct');
 assert.equal(run(first,result(false,'b')).data.results['5'].state,'correct');
});
test('unavailable storage gives an honest notice',()=>{
 assert.match(run(null,null,true).note,/cannot be saved/);
});
test('malformed stored containers are repaired',()=>{
 const data=run({results:[],bookmarks:'bad'},result(false)).data;
 assert.equal(data.results['5'].state,'incorrect');
 assert.deepEqual(data.bookmarks,[]);
});
