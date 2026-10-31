'use strict';
const $=id=>document.getElementById(id), L=window.LightweightCharts;
let symbol='BTCUSDT', interval='1h', request=0, sampleSeries=[];
const money=n=>Number.isFinite(n)?new Intl.NumberFormat('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}).format(n):'—';
const date=s=>new Date(s).toLocaleString('en-GB',{timeZone:'UTC',hour12:false})+' UTC';
const time=s=>Date.parse(s)/1000;
function chart(id){
  return L.createChart($(id),{autoSize:true,layout:{background:{color:'transparent'},textColor:'#93a6bb',fontSize:10,attributionLogo:true},grid:{vertLines:{color:'#1b2c3f66'},horzLines:{color:'#1b2c3f88'}},rightPriceScale:{borderColor:'#203246'},timeScale:{timeVisible:true,secondsVisible:false,borderColor:'#203246'},crosshair:{mode:L.CrosshairMode.Normal},handleScale:{mouseWheel:true,pinch:true},kineticScroll:{touch:!matchMedia('(prefers-reduced-motion: reduce)').matches,mouse:false}});
}
const main=chart('chart'), bt=chart('backtest-chart');
const candles=main.addSeries(L.CandlestickSeries,{upColor:'#55e3ba',downColor:'#ed889a',wickUpColor:'#55e3ba',wickDownColor:'#ed889a',borderVisible:false});
const mean=main.addSeries(L.LineSeries,{color:'#6fcfff',lineWidth:2,lineStyle:2,title:'Forecast mean',priceLineVisible:false});
const actual=bt.addSeries(L.LineSeries,{color:'#55e3ba',lineWidth:2,priceLineVisible:false});
const predicted=bt.addSeries(L.LineSeries,{color:'#6fcfff',lineWidth:2,lineStyle:2,priceLineVisible:false});
function reset(){
  candles.setData([]); mean.setData([]); actual.setData([]); predicted.setData([]);
  sampleSeries.forEach(s=>main.removeSeries(s)); sampleSeries=[];
  ['predicted','change','last','upper','lower','updated','asof','mae','rmse','direction','baseline'].forEach(id=>$(id).textContent='—');
  $('evaluation-rows').replaceChildren(); $('evaluation-count').textContent='No evaluation loaded';
  $('freshness').textContent='Awaiting data'; $('notice').hidden=false; $('notice').textContent='Loading validated model data…';
  $('status').textContent='Loading published forecast…'; $('symbol').textContent=symbol.replace('USDT',' / USDT');
}
function validate(j,s,i){
  const step=i==='1h'?3600:14400;
  if(j.schema_version!==2||j.symbol!==s||j.interval!==i||j.horizon_hours!==24||!Array.isArray(j.history)||!j.history.length||!Array.isArray(j.forecast)||j.forecast.length!==86400/step)throw Error('Invalid forecast schema');
  for(const rows of [j.history,j.forecast,...j.samples]){
    rows.forEach((r,k)=>{
      if(!Number.isFinite(time(r.timestamp))||time(r.timestamp)%step||k&&time(r.timestamp)-time(rows[k-1].timestamp)!==step||['open','high','low','close'].some(f=>!Number.isFinite(r[f])||r[f]<=0)||r.low>Math.min(r.open,r.close)||r.high<Math.max(r.open,r.close))throw Error('Invalid candle data');
    });
  }
  if(j.samples.length!==j.sample_count||j.samples.some(p=>p.length!==j.forecast.length)||j.history.at(-1).timestamp!==j.history_as_of||time(j.forecast[0].timestamp)!==time(j.history_as_of)+step||j.historical_last_close!==j.history.at(-1).close)throw Error('Inconsistent forecast origin');
  if(!Number.isFinite(time(j.completed_at))||time(j.generated_at)>time(j.completed_at)||time(j.history_as_of)+step>time(j.generated_at)||time(j.completed_at)>Date.now()/1000+60)throw Error('Invalid generation timestamps');
  for(const k of ['mae','rmse','directional_accuracy','baseline_mae'])if(!Number.isFinite(j.backtest[k])||j.backtest[k]<0)throw Error('Invalid evaluation');
  if(j.backtest.directional_accuracy>1||j.backtest.rows.length!==j.backtest.count)throw Error('Invalid evaluation count');
  return j;
}
async function load(){
  const ticket=++request,s=symbol,i=interval; reset();
  try{
    const res=await fetch('data/'+s+'_'+i+'.json',{cache:'no-store'});
    if(!res.ok)throw Error('No published forecast for this selection');
    const j=validate(await res.json(),s,i);
    if(ticket!==request)return;
    const close=j.forecast.at(-1).close,delta=100*(close/j.historical_last_close-1);
    candles.setData(j.history.map(r=>({time:time(r.timestamp),open:r.open,high:r.high,low:r.low,close:r.close})));
    const anchor={time:time(j.history_as_of),value:j.historical_last_close};
    mean.setData([anchor,...j.forecast.map(r=>({time:time(r.timestamp),value:r.close}))]);
    j.samples.forEach((path,k)=>{
      const series=main.addSeries(L.LineSeries,{color:['#55e3ba66','#c599ec77','#efbc6c77'][k%3],lineWidth:1,lineStyle:2,priceLineVisible:false,lastValueVisible:false,visible:$('scenarios').checked});
      series.setData([anchor,...path.map(r=>({time:time(r.timestamp),value:r.close}))]); sampleSeries.push(series);
    });
    main.timeScale().fitContent();
    actual.setData(j.backtest.rows.map(r=>({time:time(r.timestamp),value:r.actual})));
    predicted.setData(j.backtest.rows.map(r=>({time:time(r.timestamp),value:r.predicted}))); bt.timeScale().fitContent();
    $('predicted').textContent=money(close)+' USDT'; $('last').textContent=money(j.historical_last_close);
    $('change').textContent=(delta>=0?'+':'')+delta.toFixed(2)+'%'; $('change').style.color=delta>=0?'#55e3ba':'#ed889a';
    const ends=j.samples.map(p=>p.at(-1).close);
    $('upper').textContent=money(Math.max(...ends)); $('lower').textContent=money(Math.min(...ends));
    $('sample-note').textContent=j.sample_count+' actual model sample paths. Endpoints are not confidence bounds or guaranteed bullish/bearish outcomes.';
    $('updated').textContent=date(j.completed_at); $('asof').textContent=date(j.history_as_of);
    const expired=Date.now()/1000>=time(j.forecast.at(-1).timestamp)+(i==='1h'?3600:14400);
    const stale=Date.now()/1000-time(j.completed_at)>2*(i==='1h'?3600:14400);
    $('freshness').textContent=expired?'Expired forecast · refresh needed':stale?'Stale snapshot · refresh needed':'Published snapshot · '+j.source;
    $('status').textContent=expired?'Forecast expired':stale?'Forecast snapshot is stale':'Model forecast available';
    $('mae').textContent=money(j.backtest.mae); $('rmse').textContent=money(j.backtest.rmse);
    $('direction').textContent=(100*j.backtest.directional_accuracy).toFixed(1)+'%';
    $('baseline').textContent=money(j.backtest.baseline_mae);
    $('evaluation-count').textContent=j.backtest.folds+' held-out windows · '+j.backtest.count+' candles';
    $('method').textContent='Retrospective walk-forward evaluation: '+j.backtest.folds+' non-overlapping 24h windows; '+j.lookback+' input candles per origin. Direction compares each target close with its origin close. Baseline holds the origin price constant. Small sample; not a confidence score.';
    const fragment=document.createDocumentFragment();
    j.backtest.rows.forEach(r=>{
      const tr=document.createElement('tr');
      [date(r.timestamp),money(r.actual),money(r.predicted),money(Math.abs(r.actual-r.predicted))].forEach(v=>{const td=document.createElement('td');td.textContent=v;tr.append(td);});
      fragment.append(tr);
    });
    $('evaluation-rows').replaceChildren(fragment); $('notice').hidden=true;
  }catch(e){
    if(ticket!==request)return;
    reset(); $('status').textContent='Forecast unavailable'; $('notice').textContent=e.message+'. No simulated forecast is shown.';
  }
}
async function quotes(){
  let source='', rows=[];
  try{
    const r=await fetch('https://data-api.binance.vision/api/v3/ticker/price?symbols='+encodeURIComponent(JSON.stringify(['BTCUSDT','ETHUSDT','SOLUSDT'])),{signal:AbortSignal.timeout(10000)});
    if(!r.ok)throw Error('Binance unavailable');
    rows=await r.json(); source='Binance public market API';
  }catch{
    try{
      rows=await Promise.all(['BTC','ETH','SOL'].map(async s=>{
        const r=await fetch('https://www.okx.com/api/v5/market/ticker?instId='+s+'-USDT',{signal:AbortSignal.timeout(10000)});
        if(!r.ok)throw Error('OKX unavailable');
        const j=await r.json(); if(j.code!=='0')throw Error('OKX unavailable');
        return {symbol:s+'USDT',price:j.data[0].last};
      })); source='OKX public market API';
    }catch{
      ['BTCUSDT','ETHUSDT','SOLUSDT'].forEach(s=>$('quote-'+s).textContent='Unavailable');
      $('live-source').textContent='Live quotes unavailable · Published forecasts remain separate'; return;
    }
  }
  if(!Array.isArray(rows)||rows.length!==3||rows.some(r=>!['BTCUSDT','ETHUSDT','SOLUSDT'].includes(r.symbol)||!Number.isFinite(Number(r.price))||Number(r.price)<=0)){
    $('live-source').textContent='Live quote validation failed'; return;
  }
  rows.forEach(r=>$('quote-'+r.symbol).textContent=money(Number(r.price)));
  $('live-source').textContent='Live quotes · '+source+' · Fetched '+new Date().toISOString().slice(11,19)+' UTC · USDT · refreshes every 30s';
}
function selection(attr,value){
  document.querySelectorAll('[data-'+attr+']').forEach(b=>{
    const active=b.dataset[attr]===value;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));
  });
}
document.querySelectorAll('[data-symbol]').forEach(b=>b.addEventListener('click',()=>{symbol=b.dataset.symbol;selection('symbol',symbol);load();}));
document.querySelectorAll('[data-interval]').forEach(b=>b.addEventListener('click',()=>{interval=b.dataset.interval;selection('interval',interval);load();}));
$('scenarios').addEventListener('change',()=>sampleSeries.forEach(s=>s.applyOptions({visible:$('scenarios').checked})));
$('fit').addEventListener('click',()=>main.timeScale().fitContent());
function clock(){$('clock').textContent=new Date().toISOString().slice(11,19)+' UTC';}
clock();setInterval(clock,1000);load();quotes();setInterval(quotes,30000);
