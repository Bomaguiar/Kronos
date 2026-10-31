/* Transparent, deterministic paper-signal rules. No execution or predictive guarantees. */
(function(root){
  'use strict';
  const VERSION='spot-research-v1';
  const defaults=Object.freeze({riskPct:0.5,allocationPct:10,feePct:0.1,slippagePct:0.05,equity:null});
  const finite=x=>typeof x==='number'&&Number.isFinite(x);
  const provider=x=>x==='binance-data'?'binance':x;
  function atr(history,period=14){
    if(!Array.isArray(history)||history.length<period+1)throw Error('At least 15 completed candles are required');
    const rows=history.slice(-(period+1));
    if(rows.some(r=>!['open','high','low','close'].every(k=>finite(r[k])&&r[k]>0)||r.low>Math.min(r.open,r.close)||r.high<Math.max(r.open,r.close)))throw Error('Invalid historical candles');
    return rows.slice(1).reduce((sum,r,i)=>sum+Math.max(r.high-r.low,Math.abs(r.high-rows[i].close),Math.abs(r.low-rows[i].close)),0)/period;
  }
  function position(plan,settings){
    const {equity,riskPct,allocationPct}=settings;
    if(equity===null)return null;
    if(!finite(equity)||equity<=0||equity>1e12)throw Error('Enter an account balance above zero');
    const budget=equity*riskPct/100;
    const unitCash=plan.entry*(1+plan.costRate);
    const byRisk=budget/plan.lossPerUnit;
    const byAllocation=equity*allocationPct/100/unitCash;
    // Floor for conservative display; this is not an exchange lot-size calculation.
    const units=Math.floor(Math.min(byRisk,byAllocation)*1e8)/1e8;
    return {units,riskBudget:budget,estimatedStopLoss:units*plan.lossPerUnit,notional:units*plan.entry,cashRequired:units*unitCash,allocationLimited:byAllocation<byRisk};
  }
  function evaluate(data,quote=null,options={},now=Date.now()){
    const settings={...defaults,...options}, reasons=[], checks=[];
    const result={version:VERSION,action:'NO TRADE',bias:'Unavailable',plan:null,size:null,reasons,checks};
    function check(name,pass,reason){checks.push({name,pass:Boolean(pass)});if(!pass)reasons.push(reason);}
    try{
      for(const [name,min,max] of [['riskPct',0.01,2],['allocationPct',1,100],['feePct',0,2],['slippagePct',0,2]]){
        if(!finite(settings[name])||settings[name]<min||settings[name]>max)throw Error('Invalid '+name+' assumption');
      }
      if(!data||data.schema_version!==2||!['1h','4h'].includes(data.interval)||!['BTCUSDT','ETHUSDT','SOLUSDT'].includes(data.symbol))throw Error('Awaiting a validated forecast');
      const step=(data.interval==='1h'?3600:14400)*1000;
      const origin=Date.parse(data.history_as_of), generated=Date.parse(data.generated_at), completed=Date.parse(data.completed_at);
      if(![origin,generated,completed,now].every(Number.isFinite)||origin+step>generated||generated>completed||completed>now+60000)throw Error('Invalid forecast timestamps');
      const anchor=data.historical_last_close, end=data.forecast?.at(-1)?.close;
      if(!finite(anchor)||anchor<=0||!finite(end)||end<=0||data.history?.at(-1)?.close!==anchor)throw Error('Invalid model prices');
      const volatility=atr(data.history);
      if(!finite(volatility)||volatility<=0)throw Error('Insufficient historical volatility');
      result.bias=end>anchor?'Bullish':end<anchor?'Bearish':'Neutral';
      result.modelMovePct=100*(end/anchor-1);
      const entryLow=anchor-0.1*volatility, entry=anchor+0.1*volatility;
      const swingLow=Math.min(...data.history.slice(-5).map(r=>r.low));
      const stop=Math.min(anchor-1.5*volatility,swingLow-0.1*volatility);
      if(stop<=0||entryLow<=stop)throw Error('Cannot construct positive stop/entry levels');
      const costRate=(settings.feePct+settings.slippagePct)/100;
      const lossPerUnit=entry*(1+costRate)-stop*(1-costRate);
      const target1=(entry*(1+costRate)+lossPerUnit)/(1-costRate);
      const target2=(entry*(1+costRate)+2*lossPerUnit)/(1-costRate);
      const modelReward=end*(1-costRate)-entry*(1+costRate);
      const modelRR=modelReward/lossPerUnit;
      const expiresAt=Math.min(origin+2*step,generated+step);
      const timeExit=origin+step+24*3600000;
      const plan={anchor,entryLow,entry,stop,target1,target2,atr:volatility,costRate,lossPerUnit,modelRR,modelEndpoint:end,expiresAt,timeExit};
      result.plan=plan;
      check('Fresh setup',now>=completed&&now<expiresAt,'Setup expired or not yet available; regenerate the forecast before considering an entry.');
      const b=data.backtest;
      if(!b||!finite(b.mae)||b.mae<0||!finite(b.baseline_mae)||b.baseline_mae<0||!finite(b.directional_accuracy)||b.directional_accuracy<0||b.directional_accuracy>1||!Number.isInteger(b.folds)||!Number.isInteger(b.count)||b.count!==b.folds*(86400000/step))throw Error('Invalid backtest statistics');
      check('Ten evaluation windows',b.folds>=10,'Fewer than ten historical evaluation windows; evidence is too limited for this screen.');
      check('Model beats baseline',b.baseline_mae>0&&b.mae<=0.9*b.baseline_mae,'Model MAE does not beat the unchanged-price baseline by at least 10%.');
      check('Direction screen',b.directional_accuracy>=0.55,'Historical directional accuracy is below the illustrative 55% screen.');
      check('Bullish model bias',end>entry,'Model does not support a new spot-long entry. No short-selling signal is issued.');
      if(!Array.isArray(data.samples)||data.samples.length!==data.sample_count||data.samples.length<3||data.samples.some(p=>!finite(p.at(-1)?.close)||p.at(-1).close<=0))throw Error('At least three valid model sample paths are required');
      const support=data.samples.filter(p=>p.at(-1).close*(1-costRate)>entry*(1+costRate)).length;
      result.sampleSupport=support+'/'+data.samples.length;
      check('Sample direction agreement',support===data.samples.length,'Not all sampled endpoints cover the assumed entry and exit costs. Sample agreement is not a probability.');
      check('Move exceeds typical error',end-entry>b.mae,'Projected upside is no larger than the historical MAE.');
      check('Net reward/risk at least 2',modelRR>=2,'Model endpoint does not support the second target at 2:1 reward/risk after assumed costs.');
      const quoteValid=quote&&finite(quote.price)&&quote.price>0&&finite(quote.fetchedAt)&&quote.fetchedAt<=now&&now-quote.fetchedAt<=60000&&quote.symbol===data.symbol&&provider(quote.source)===provider(data.source);
      check('Fresh same-exchange quote',quoteValid,'A quote fetched within 60 seconds from the forecast exchange is required.');
      check('Price inside entry zone',quoteValid&&quote.price>=entryLow&&quote.price<=entry,'Current price is outside the entry zone or unavailable. Do not chase the price.');
      if(quoteValid&&quote.price<=stop)check('Stop not breached',false,'Current price has breached the hypothetical stop; setup is invalidated.');
      result.size=position(plan,settings);
      if(reasons.length===0)result.action='PAPER LONG';
    }catch(error){
      reasons.push(error.message);result.action='NO TRADE';result.size=null;
      if(!checks.length)result.plan=null;
    }
    return result;
  }
  const api={VERSION,defaults,atr,position,evaluate};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  if(root)root.KronosSignals=api;
})(typeof window!=='undefined'?window:null);
