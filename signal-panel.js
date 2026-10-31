/* Inputs remain in memory on this page; they are never saved or transmitted. */
(function(){
  'use strict';
  const el=id=>document.getElementById(id);
  let snapshot=null,quotes=new Map();
  const format=x=>Number.isFinite(x)?new Intl.NumberFormat('en-US',{maximumFractionDigits:2,minimumFractionDigits:2}).format(x):'—';
  const utc=x=>new Date(x).toLocaleString('en-GB',{timeZone:'UTC',hour12:false})+' UTC';
  function settings(){
    return {equity:el('signal-equity').value===''?null:Number(el('signal-equity').value),riskPct:Number(el('signal-risk').value),allocationPct:Number(el('signal-allocation').value),feePct:Number(el('signal-fee').value),slippagePct:Number(el('signal-slippage').value)};
  }
  function render(){
    const result=KronosSignals.evaluate(snapshot,snapshot?quotes.get(snapshot.symbol):null,settings());
    el('signal-action').textContent=result.action;
    el('signal-action').className='signal-action '+(result.action==='PAPER LONG'?'qualified':'blocked');
    el('signal-market').textContent=snapshot?snapshot.symbol.replace('USDT',' / USDT')+' · '+snapshot.interval.toUpperCase():'Awaiting forecast';
    el('signal-bias').textContent=result.bias+(Number.isFinite(result.modelMovePct)?' model bias · '+(result.modelMovePct>=0?'+':'')+result.modelMovePct.toFixed(2)+'%':'');
    el('signal-reasons').replaceChildren(...result.reasons.map(reason=>{const li=document.createElement('li');li.textContent=reason;return li;}));
    el('signal-pass').hidden=result.reasons.length!==0;
    el('signal-checks').replaceChildren(...result.checks.map(check=>{const span=document.createElement('span');span.className=check.pass?'check-pass':'check-fail';span.textContent=(check.pass?'✓ ':'× ')+check.name;return span;}));
    const p=result.plan;
    el('signal-entry').textContent=p?format(p.entryLow)+' – '+format(p.entry):'—';
    el('signal-stop').textContent=p?format(p.stop):'—';
    el('signal-tp1').textContent=p?format(p.target1):'—';
    el('signal-tp2').textContent=p?format(p.target2):'—';
    el('signal-rr').textContent=p?p.modelRR.toFixed(2)+':1':'—';
    el('signal-atr').textContent=p?format(p.atr):'—';
    el('signal-expires').textContent=p?utc(p.expiresAt):'—';
    el('signal-time-exit').textContent=p?utc(p.timeExit):'—';
    el('signal-samples').textContent=result.sampleSupport?result.sampleSupport+' endpoints exceed costs; not a confidence score':'—';
    el('signal-plan-label').textContent=result.action==='PAPER LONG'?'Conditional paper setup · USDT':'Hypothetical levels only · no active entry · USDT';
    const size=result.size;
    el('signal-size').textContent=size?size.units.toLocaleString('en-US',{maximumFractionDigits:8})+' '+snapshot.symbol.replace('USDT',''):'Enter an account balance';
    el('signal-notional').textContent=size?format(size.notional)+' USDT':'—';
    el('signal-loss').textContent=size?format(size.estimatedStopLoss)+' USDT':'—';
    el('signal-budget').textContent=size?format(size.riskBudget)+' USDT':'—';
    el('signal-size-note').textContent=size?(size.allocationLimited?'Size limited by the allocation cap. ':'Size limited by the risk budget. ')+(result.action==='NO TRADE'?'Hypothetical calculation only; the signal is NO TRADE. ':'Paper calculation only. '):'Account balance stays in this page’s memory. No account connection or data upload.';
  }
  document.addEventListener('kronos:data',e=>{snapshot=e.detail;render();});
  document.addEventListener('kronos:quotes',e=>{quotes=new Map(e.detail.map(q=>[q.symbol,q]));render();});
  ['signal-equity','signal-risk','signal-allocation','signal-fee','signal-slippage'].forEach(id=>el(id).addEventListener('input',render));
  render();setInterval(render,1000);
})();
