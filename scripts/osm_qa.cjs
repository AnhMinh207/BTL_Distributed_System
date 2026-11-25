/* Live browser QA: real Leaflet, real OSM tiles, real pointer selection/drag. */
const {chromium}=require('../runtime/browser-qa/node_modules/playwright');
const fs=require('node:fs');const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_PATH||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});const checks=[],errors=[],googleRequests=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/googleapis|gstatic/.test(r.url()))googleRequests.push(r.url());});
 try{
  await page.goto(process.env.APP_URL||'http://127.0.0.1:8088',{waitUntil:'networkidle'});
  await page.waitForFunction(()=>window.GoRideMap?.ready&&window.GoRideMap.loadedTiles>0,{},{timeout:30000});
  assert.equal(await page.locator('#map-message').isVisible(),false);
  const tiles=await page.locator('.leaflet-tile-loaded').evaluateAll(images=>images.filter(i=>i.naturalWidth>0).length);assert.ok(tiles>0);
  checks.push('Real OpenStreetMap street tiles load successfully');
  await page.locator('.leaflet-control-attribution a[href*="openstreetmap"]').waitFor();checks.push('Visible OpenStreetMap attribution is retained');
  await page.locator('[data-map-target="pickup"]').click();await page.waitForTimeout(600);
  let box=await page.locator('#ride-map').boundingBox();
  await page.evaluate(()=>window.GoRideMap.map.once('click',event=>{window.lastTestMapClick=[event.latlng.lat,event.latlng.lng];}));
  await page.mouse.click(box.x+box.width*.45,box.y+box.height*.43);
  await page.waitForFunction(()=>document.querySelector('#pickup-address').value==='Điểm đón đã chọn');
  const expected=await page.evaluate(()=>window.lastTestMapClick);
  assert.ok(Math.abs(Number(await page.locator('#pickup-lat').inputValue())-expected[0])<.00002);
  assert.ok(Math.abs(Number(await page.locator('#pickup-lon').inputValue())-expected[1])<.00002);
  checks.push('Pointer click fills pickup with real geographic coordinates');
  await page.waitForTimeout(400);
  const before=await page.locator('#pickup-lat').inputValue();
  box=await page.locator('.osm-marker.pickup').boundingBox();
  await page.mouse.move(box.x+17,box.y+16);await page.mouse.down();await page.mouse.move(box.x+57,box.y+51,{steps:10});await page.mouse.up();
  await page.waitForTimeout(400);assert.notEqual(await page.locator('#pickup-lat').inputValue(),before);
  checks.push('Dragging pickup marker updates coordinates');
  const center=await page.evaluate(()=>{const m=window.GoRideMap.map;m.panBy([60,25],{animate:false});return [m.getCenter().lat,m.getCenter().lng];});
  await page.waitForTimeout(2300);
  const after=await page.evaluate(()=>[window.GoRideMap.map.getCenter().lat,window.GoRideMap.map.getCenter().lng]);
  assert.ok(Math.abs(center[0]-after[0])<.00001);checks.push('Background polling does not reset the viewport');
  // Restore normal locations for screenshot and verify mobile map layout.
  await page.evaluate(()=>{chooseAddress('pickup',{name:'Phố đi bộ Nguyễn Huệ',location:[10.7769,106.7009],address:'TP. Hồ Chí Minh'});chooseAddress('destination',{name:'Thảo Cầm Viên',location:[10.79,106.72],address:'TP. Hồ Chí Minh'});});
  await page.waitForTimeout(500);await page.screenshot({path:'docs/ui-osm-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.waitForTimeout(600);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await page.screenshot({path:'docs/ui-osm-mobile.png',fullPage:true});checks.push('Mobile map resizes without horizontal overflow');
  await page.setViewportSize({width:1440,height:1000});
  await page.locator('.demo-menu > summary').click();await page.locator('#demo-setup').click();
  await page.locator('[data-role="driver"]').waitFor();
  await page.waitForFunction(()=>!document.querySelector('#demo-setup').disabled);
  await page.locator('#book-button').click();
  await page.waitForFunction(()=>document.querySelector('#trip-badge').textContent==='Chờ tài xế nhận',{},{timeout:30000});
  assert.equal(await page.evaluate(()=>window.GoRideMap.markers.pickup.dragging.enabled()),false);
  const locked=await page.locator('#pickup-lat').inputValue();
  await page.locator('[data-map-target="pickup"]').click();
  assert.equal(await page.locator('#pickup-lat').inputValue(),locked);
  page.on('dialog',dialog=>dialog.accept());await page.locator('[data-action="cancel"]').click();
  await page.waitForFunction(()=>document.querySelector('#trip-badge').textContent==='Đã hủy');
  checks.push('Active-trip marker dragging is locked and cancellation still works');
  assert.deepEqual(googleRequests,[]);assert.deepEqual(errors,[]);checks.push('No Google API calls and no uncaught JavaScript errors');
  fs.writeFileSync('docs/osm-map-results.json',JSON.stringify({passed:checks.length,checks,real_tiles_loaded:tiles,provider:'OpenStreetMap / Leaflet 1.9.4',api_key_required:false},null,2));
  console.log(JSON.stringify({passed:checks.length,checks},null,2));
 }catch(e){await page.screenshot({path:'runtime/osm-failure.png',fullPage:true}).catch(()=>{});throw e;}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
