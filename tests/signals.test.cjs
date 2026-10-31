'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const S=require('../signals.js');
const now=Date.parse('2026-01-20T11:10:00Z');
function fixture(){
 const last=Date.parse('2026-01-20T10:00:00Z');
 const history=Array.from({length:20},(_,i)=>({timestamp:new Date(last-(19-i)*3600000).toISOString(),open:100,high:101,low:99,close:100}));
 const future=Array.from({length:24},(_,i)=>({timestamp:new Date(last+(i+1)*3600000).toISOString(),open:100,high:115,low:99,close:112}));
 return {schema_version:2,symbol:'BTCUSDT',interval:'1h',source:'binance',history_as_of:history.at(-1).timestamp,generated_at:'2026-01-20T11:05:00Z',completed_at:'2026-01-20T11:06:00Z',historical_last_close:100,history,forecast:future,sample_count:3,samples:[110,112,114].map(v=>future.map(r=>({...r,close:v}))),backtest:{folds:10,count:240,mae:1,baseline_mae:2,directional_accuracy:0.7}};
}
const quote=()=>({symbol:'BTCUSDT',price:100,source:'binance-data',fetchedAt:now-5000});
function run(d=fixture(),q=quote(),o={},t=now){return S.evaluate(d,q,o,t);}
test('qualified data produces only a paper long',()=>assert.equal(run().action,'PAPER LONG'));
test('ATR uses true range including gaps',()=>{
 const h=fixture().history;h.at(-1).high=111;h.at(-1).low=109;h.at(-1).open=110;h.at(-1).close=110;
 assert.equal(S.atr(h),(13*2+11)/14);
});
test('stop below entry; exact net targets incorporate both costs',()=>{
 const p=run().plan;assert(p.stop<p.entryLow&&p.entryLow<p.entry&&p.entry<p.target1&&p.target1<p.target2);
 for(const [target,r] of [[p.target1,1],[p.target2,2]])assert(Math.abs((target*(1-p.costRate)-p.entry*(1+p.costRate))/p.lossPerUnit-r)<1e-10);
});
test('sizing respects risk, cash and allocation caps',()=>{
 const r=run(undefined,undefined,{equity:10000});assert(r.size.estimatedStopLoss<=50);assert(r.size.cashRequired<=1000);
 assert.equal(r.size.allocationLimited,true);
});
test('small allocation cannot silently leverage',()=>assert(run(undefined,undefined,{equity:100,allocationPct:1}).size.cashRequired<=1));
test('missing account never invents a balance',()=>assert.equal(run().size,null));
test('bad risk and account values fail closed',()=>{
 for(const o of [{riskPct:NaN},{riskPct:-1},{riskPct:3},{allocationPct:101},{feePct:-1},{equity:Infinity},{equity:0}])assert.equal(run(undefined,undefined,o).action,'NO TRADE');
});
test('stale and future quotes fail closed',()=>{
 for(const age of [60001,-1])assert.equal(run(undefined,{...quote(),fetchedAt:now-age}).action,'NO TRADE');
});
test('unavailable, wrong-market and cross-exchange quotes fail closed',()=>{
 for(const q of [null,{...quote(),symbol:'ETHUSDT'},{...quote(),source:'okx'},{...quote(),price:NaN}])assert.equal(run(undefined,q).action,'NO TRADE');
});
test('no price chasing above or below entry zone',()=>{
 for(const price of [99,101,90])assert.equal(run(undefined,{...quote(),price}).action,'NO TRADE');
});
test('setup expiry checked every evaluation',()=>assert.equal(run(undefined,{...quote(),fetchedAt:now+3600000},{},now+3600000).action,'NO TRADE'));
test('weak, absent or short backtest cannot qualify',()=>{
 for(const b of [{folds:3,count:72},{mae:3},{directional_accuracy:0.2},{baseline_mae:0},{count:1},{mae:NaN}]){const d=fixture();Object.assign(d.backtest,b);assert.equal(run(d).action,'NO TRADE');}
});
test('sample disagreement and short horizon upside cannot qualify',()=>{
 const d=fixture();d.samples[0].at(-1).close=99;assert.equal(run(d).action,'NO TRADE');
 const e=fixture();e.forecast.at(-1).close=101;assert.equal(run(e).action,'NO TRADE');
});
test('bearish data never issues a short',()=>{const d=fixture();d.forecast.at(-1).close=90;assert.equal(run(d).action,'NO TRADE');assert.equal(run(d).bias,'Bearish');});
test('invalid data and zero volatility fail closed',()=>{
 for(const d of [null,{}, {...fixture(),generated_at:'bad'}])assert.equal(run(d).action,'NO TRADE');
 const d=fixture();d.history.forEach(r=>{r.high=r.low=100;});assert.equal(run(d).action,'NO TRADE');
});
test('invalid settings never leak stale plan into output',()=>assert.equal(run(undefined,undefined,{riskPct:NaN}).plan,null));
