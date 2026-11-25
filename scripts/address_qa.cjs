/* Optional browser test for address selection, live geocoding and failure fallback. */
const {chromium}=require('../runtime/browser-qa/node_modules/playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_PATH||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
  const page=await browser.newPage({viewport:{width:1440,height:1000}});const checks=[],errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  try{
    await page.goto(process.env.APP_URL||'http://127.0.0.1:8088',{waitUntil:'networkidle'});
    const input=page.locator('#destination-address');
    await input.fill('ben xe mien tay');
    await page.locator('#destination-results .address-option').filter({hasText:'Bến xe Miền Tây'}).click();
    assert.ok((await input.inputValue()).includes('Bến xe Miền Tây'));
    assert.equal(await page.locator('#book-button').isDisabled(),false);
    checks.push('Accent-insensitive catalog search selects a real coordinate');
    await input.fill('Louvre Paris');
    assert.equal(await page.locator('#book-button').isDisabled(),true);
    const live=await page.waitForResponse(r=>r.url().includes('/api/places/search?')&&r.url().includes('Louvre'),{timeout:15000});
    assert.equal(live.status(),200);
    const data=await live.json();assert.ok(data.places.length>0,'Live geocoder returned no results');
    await page.locator('#destination-results .address-option').first().click();
    const actualLat=Number(await page.locator('#destination-lat').inputValue());
    assert.ok(Math.abs(actualLat-data.places[0].location[0])<.00002);
    checks.push('Free-text lookup outside the catalog resolves through live Photon');
    await page.locator('#pickup-address').fill('10.8,106.7');
    await page.locator('#pickup-results .address-option').first().click();
    assert.equal(Number(await page.locator('#pickup-lat').inputValue()),10.8);
    checks.push('Pasted latitude/longitude is selectable');
    await page.route('**/api/places/search?**',route=>route.fulfill({status:503,contentType:'application/json',body:'{"error":"offline"}'}));
    await input.fill('dia chi chua xac nhan');
    await page.waitForTimeout(1200);
    await page.locator('#destination-results').getByText('Chưa kết nối được tìm kiếm.',{exact:false}).waitFor();
    assert.equal(await page.locator('#book-button').isDisabled(),true);
    checks.push('An unresolved address cannot silently book with old coordinates');
    await input.fill('cho ben thanh');
    await page.locator('#destination-results .address-option').first().click();
    assert.equal(await page.locator('#book-button').isDisabled(),false);
    checks.push('Local catalog remains usable when online search is offline');
    await page.unroute('**/api/places/search?**');
    await input.fill('cong vien');
    await input.press('ArrowDown');await input.press('Enter');
    assert.ok((await input.inputValue()).startsWith('Công viên'));
    checks.push('Keyboard selection with arrow keys and Enter works');
    await page.setViewportSize({width:390,height:844});
    await input.fill('dai hoc');
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    await page.screenshot({path:'docs/ui-address-search.png',fullPage:true});
    checks.push('Address suggestions fit a 390px mobile screen');
    assert.deepEqual(errors,[]);checks.push('No uncaught JavaScript errors');
    fs.writeFileSync('docs/address-test-results.json',JSON.stringify({passed:checks.length,checks,live_provider:'Photon / OpenStreetMap',live_query:'Louvre Paris'},null,2));
    console.log(JSON.stringify({passed:checks.length,checks},null,2));
  }catch(e){await page.screenshot({path:'runtime/address-failure.png',fullPage:true}).catch(()=>{});throw e;}
  finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
