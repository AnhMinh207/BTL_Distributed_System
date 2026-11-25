const {chromium}=require('../runtime/browser-qa/node_modules/playwright');
const fs=require('node:fs');const assert=require('node:assert/strict');
(async()=>{
 const key=fs.readFileSync('.env','utf8').split(/\r?\n/).find(s=>s.startsWith('OPERATIONS_KEY=')).split('=').slice(1).join('=');
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(process.env.APP_URL||'http://127.0.0.1:8180',{waitUntil:'networkidle'});
  await page.locator('.nav-item[data-view="system"]').click();
  await page.locator('#operations-key').fill('wrong-key');await page.locator('#operations-login button').click();
  await page.locator('#operations-error').filter({hasText:'không đúng'}).waitFor();
  await page.locator('#operations-key').fill(key);await page.locator('#operations-login button').click();
  await page.locator('#operations-overview table').first().waitFor();
  assert.equal(await page.locator('#operations-key').inputValue(),'');
  assert.equal(await page.locator('#operations-overview table').first().locator('tbody tr').count(),9);
  const trace=await page.locator('#trace-list tbody tr td').first().textContent();
  await page.locator('#trace-id').fill(trace);await page.locator('#trace-search button').click();
  await page.locator('#trace-detail tbody tr').first().waitFor();
  assert.ok(await page.locator('#operations-logs tbody tr').count()>0);
  await page.screenshot({path:'docs/ui-operations.png',fullPage:true});
  await page.locator('#operations-logout').click();assert.equal(await page.locator('#operations-data').isVisible(),false);
  assert.deepEqual(errors,[]);
  fs.writeFileSync('docs/operations-browser-results.json',JSON.stringify({passed:6,checks:['Reject invalid operations key','Accept valid key without displaying it','Nine service metrics rows','Trace detail loads','Central logs visible','Disconnect clears view; no JS errors']},null,2));
  console.log('Operations browser: 6/6 checks passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
