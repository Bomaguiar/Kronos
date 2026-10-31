/* Browser QA without opening a listening port: route requests to local static files. */
const { chromium } = require('playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
(async()=>{
  const root=process.cwd(), output=path.join(root,'test-results');fs.mkdirSync(output,{recursive:true});
  const browser=await chromium.launch({headless:true,channel:'chrome'});
  let total=0;
  for(const viewport of [{width:1440,height:1100},{width:390,height:844}]){
    const context=await browser.newContext({viewport,reducedMotion:'reduce'});
    const page=await context.newPage();const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
    await page.route('https://kronos.test/**',async route=>{
      const url=new URL(route.request().url()), relative=decodeURIComponent(url.pathname).replace(/^\//,'')||'index.html';
      const file=path.resolve(root,relative);
      if(!file.startsWith(root+path.sep)||!fs.existsSync(file)){await route.fulfill({status:404,body:'Not found'});return;}
      const types={'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json'};
      await route.fulfill({status:200,contentType:types[path.extname(file)]||'text/plain',body:fs.readFileSync(file)});
    });
    await page.goto(process.env.DASHBOARD_URL||'https://kronos.test/',{waitUntil:'networkidle'});
    for(const symbol of ['BTCUSDT','ETHUSDT','SOLUSDT']){
      await page.locator('[data-symbol="'+symbol+'"]').click();
      for(const interval of ['1h','4h']){
        await page.locator('[data-interval="'+interval+'"]').click();
        await page.waitForFunction(()=>document.getElementById('notice').hidden,{timeout:20000});
        assert((await page.locator('#predicted').innerText()).includes('USDT'));
        assert.equal(await page.locator('#evaluation-rows tr').count(),JSON.parse(fs.readFileSync(path.join(root,'data',symbol+'_'+interval+'.json'),'utf8')).backtest.count);
        assert.equal(await page.locator('#symbol').innerText(),symbol.replace('USDT',' / USDT'));
        assert(await page.locator('#chart canvas').count()>0);
        assert(['NO TRADE','PAPER LONG'].includes(await page.locator('#signal-action').innerText()));
        assert.notEqual(await page.locator('#signal-stop').innerText(),'—');
        total++;
      }
    }
    // Exercise switching races, scenario visibility, reset, disclosure and mobile overflow.
    await page.locator('[data-symbol="BTCUSDT"]').click();
    await page.locator('[data-interval="1h"]').click();
    await page.waitForFunction(()=>document.getElementById('notice').hidden);
    await page.locator('#scenarios').uncheck();await page.locator('#scenarios').check();await page.locator('#fit').click();
    await page.locator('#signal-equity').fill('10000');
    await page.locator('#signal-risk').fill('1');
    assert((await page.locator('#signal-notional').innerText()).includes('USDT'));
    await page.locator('#signal-equity').fill('');
    assert.equal(await page.locator('#signal-size').innerText(),'Enter an account balance');
    await page.locator('summary').last().click();
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(output,'dashboard-'+viewport.width+'.png'),fullPage:true});
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({viewport,consoleErrors:errors,liveQuotes:await page.locator('#live-source').innerText(),selections:6}));
    await context.close();
  }
  await browser.close(); console.log('PASS '+total+' asset/timeframe/viewport combinations');
})().catch(e=>{console.error(e);process.exit(1)});
