/* GoRide: public API client. Every booking and lifecycle change goes to real services. */
'use strict';
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const icons = {
  car:'<path d="m5 8 2-4h10l2 4M3 10l2-2h14l2 2v8H3zM5 18v2m14-2v2M7 12h.01M17 12h.01M8 16h8"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  wallet:'<path d="M20 7H5a2 2 0 0 1 0-4h13v4M4 7v13h17V7m0 5h-6v4h6M17 14h.01"/>',
  bell:'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
  pin:'<path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 0 1 14 0Z"/><circle cx="12" cy="10" r="2.5"/>',
  layers:'<path d="m12 3 9 5-9 5-9-5 9-5ZM3 12l9 5 9-5M3 16l9 5 9-5"/>',
  spark:'<path d="m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3 3-7Z"/>',
  'arrow-up-right':'<path d="M6 18 18 6M6 6h12v12"/>',
  eye:'<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
  route:'<circle cx="6" cy="5" r="2"/><circle cx="18" cy="19" r="2"/><path d="M6 7v6a4 4 0 0 0 4 4h4a4 4 0 0 0 0-8h-2"/>',
  locate:'<circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/><path d="M12 2v4m0 12v4M2 12h4m12 0h4"/>',
  play:'<path d="m8 4 12 8-12 8V4Z"/>',
  shield:'<path d="m12 2 8 3v6c0 6-8 11-8 11S4 17 4 11V5l8-3Z"/><path d="m8 12 3 3 5-6"/>',
  user:'<circle cx="12" cy="8" r="4"/><path d="M4 22v-2a8 8 0 0 1 16 0v2"/>'
};
const icon = (name) => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${icons[name] || icons.route}</svg>`;
function hydrateIcons(root = document) { root.querySelectorAll('[data-icon]').forEach(el => { el.innerHTML = icon(el.dataset.icon); }); }
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = (value) => new Intl.NumberFormat('vi-VN').format(value || 0) + ' ₫';
const shortId = (value) => value ? value.slice(0, 8).toUpperCase() : '—';
const date = (value) => new Date(value * 1000).toLocaleString('vi-VN', {hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit'});
const terminal = new Set(['completed', 'cancelled', 'payment_failed']);
const labels = {requested:'Đang tìm tài xế',offered:'Chờ tài xế nhận',accepted:'Tài xế đang đến',in_progress:'Đang di chuyển',awaiting_payment:'Đang thanh toán',completed:'Đã hoàn tất',cancelled:'Đã hủy',payment_failed:'Thanh toán thất bại'};
const topicLabels = {'trip.requested':'Đã tiếp nhận yêu cầu đặt xe','driver.reserved':'Đã tìm thấy tài xế phù hợp','matching.failed':'Chưa tìm thấy tài xế trong khu vực','trip.accepted':'Tài xế đã nhận chuyến','trip.started':'Hành trình đã bắt đầu','trip.completed':'Chuyến đi kết thúc, đang thanh toán','trip.cancelled':'Chuyến đi đã hủy','payment.succeeded':'Thanh toán thành công','payment.failed':'Thanh toán bị từ chối'};
const places = [
  ['Nhà thờ Đức Bà',10.7798,106.6990], ['Phố đi bộ Nguyễn Huệ',10.7769,106.7009],
  ['Thảo Cầm Viên',10.7900,106.7200], ['Chợ Bến Thành',10.7725,106.6980],
  ['Dinh Độc Lập',10.7770,106.6953], ['Bến Bạch Đằng',10.7765,106.7068],
  ['Sân bay Tân Sơn Nhất, TP. Hồ Chí Minh',10.8130,106.6625],
  ['Ga Sài Gòn, TP. Hồ Chí Minh',10.7824,106.6775],
  ['Bến xe Miền Đông mới, TP. Thủ Đức',10.8796,106.8156],
  ['Bến xe Miền Tây, TP. Hồ Chí Minh',10.7408,106.6187],
  ['Landmark 81, Bình Thạnh, TP. Hồ Chí Minh',10.7950,106.7219],
  ['Bitexco Financial Tower, TP. Hồ Chí Minh',10.7717,106.7044],
  ['Bưu điện Trung tâm, TP. Hồ Chí Minh',10.7799,106.6999],
  ['Nhà hát Thành phố, TP. Hồ Chí Minh',10.7768,106.7031],
  ['Bảo tàng Chứng tích Chiến tranh, TP. Hồ Chí Minh',10.7795,106.6921],
  ['Công viên Tao Đàn, TP. Hồ Chí Minh',10.7758,106.6867],
  ['Công viên Lê Văn Tám, TP. Hồ Chí Minh',10.7882,106.6934],
  ['Công viên Gia Định, TP. Hồ Chí Minh',10.8117,106.6749],
  ['AEON Mall Tân Phú, TP. Hồ Chí Minh',10.8014,106.6177],
  ['AEON Mall Bình Tân, TP. Hồ Chí Minh',10.7424,106.6113],
  ['Crescent Mall, Quận 7, TP. Hồ Chí Minh',10.7284,106.7182],
  ['SC VivoCity, Quận 7, TP. Hồ Chí Minh',10.7297,106.7032],
  ['Đại học Bách khoa, TP. Hồ Chí Minh',10.7734,106.6606],
  ['Đại học Khoa học Tự nhiên, TP. Hồ Chí Minh',10.7629,106.6822],
  ['Đại học Sư phạm Kỹ thuật, TP. Thủ Đức',10.8506,106.7719],
  ['Bệnh viện Chợ Rẫy, TP. Hồ Chí Minh',10.7579,106.6595],
  ['Bệnh viện Đại học Y Dược, TP. Hồ Chí Minh',10.7555,106.6648],
  ['Bệnh viện Nhân dân 115, TP. Hồ Chí Minh',10.7747,106.6678],
  ['Hồ Hoàn Kiếm, Hà Nội',21.0287,105.8523],
  ['Nhà hát Lớn, Hà Nội',21.0242,105.8577],
  ['Văn Miếu Quốc Tử Giám, Hà Nội',21.0276,105.8355],
  ['Lăng Chủ tịch Hồ Chí Minh, Hà Nội',21.0369,105.8347],
  ['Hồ Tây, Hà Nội',21.0584,105.8229],
  ['Sân bay Nội Bài, Hà Nội',21.2187,105.8042],
  ['Ga Hà Nội',21.0251,105.8413],
  ['Đại học Bách khoa Hà Nội',21.0070,105.8431],
  ['Bến xe Mỹ Đình, Hà Nội',21.0282,105.7788],
  ['Cầu Rồng, Đà Nẵng',16.0611,108.2274],
  ['Sân bay Đà Nẵng',16.0439,108.1993],
  ['Biển Mỹ Khê, Đà Nẵng',16.0544,108.2470],
  ['Chợ Hàn, Đà Nẵng',16.0678,108.2240],
  ['Phố cổ Hội An, Quảng Nam',15.8770,108.3280],
  ['Đại Nội Huế',16.4698,107.5770],
  ['Chợ Đầm, Nha Trang',12.2548,109.1885],
  ['Chợ Đà Lạt',11.9424,108.4370],
  ['Bến Ninh Kiều, Cần Thơ',10.0320,105.7897],
  ['Bãi Sau, Vũng Tàu',10.3407,107.0920],
  ['Tọa độ tùy chọn',null,null]
];
const state = {sessions:{},role:'passenger',view:'ride',trips:[],payments:[],notices:[],driver:null,
  selected:null,services:{},authMode:'login',busy:false,demo:false,mapTarget:null,
  demoSteps:[],nonce:0,refreshing:false,lastHeartbeat:0,pendingBooking:null,authOpen:false,driverProfileUser:null};
try {
  const stored = JSON.parse(sessionStorage.getItem('goride.sessions') || '{}');
  for (const role of ['passenger','driver']) if (stored[role]?.token && stored[role]?.id && stored[role]?.role === role) state.sessions[role] = stored[role];
  const storedRole = sessionStorage.getItem('goride.role');
  state.role = state.sessions[storedRole] ? storedRole : (state.sessions.passenger ? 'passenger' : 'driver');
  state.pendingBooking = JSON.parse(sessionStorage.getItem('goride.pending') || 'null');
} catch { /* Browser storage may be disabled; in-memory sessions remain usable. */ }
function persist() {
  try {
    sessionStorage.setItem('goride.sessions', JSON.stringify(state.sessions));
    sessionStorage.setItem('goride.role', state.role);
    sessionStorage.setItem('goride.pending', JSON.stringify(state.pendingBooking));
  } catch { /* Do not expose tokens through errors or fall back to URLs. */ }
}
const session = () => state.sessions[state.role];
function toast(message, error = false) {
  const el = document.createElement('div'); el.className = 'toast' + (error ? ' error' : '');
  el.textContent = message; $('#toast-region').append(el); setTimeout(() => el.remove(), error ? 8000 : 4500);
}
const errorTranslations = {
  'Service unavailable':'Dịch vụ đang mất kết nối. Dữ liệu đã gửi có thể còn đang xử lý; vui lòng làm mới trước khi thử lại.',
  'Invalid credentials':'Tên đăng nhập hoặc mật khẩu chưa đúng.', 'Username already exists':'Tên đăng nhập đã được sử dụng.',
  'Passenger already has active trip':'Bạn đang có một chuyến chưa kết thúc. Hãy kiểm tra hành trình hiện tại.',
  'Driver has active trip':'Bạn đang có chuyến. Hãy hoàn tất hoặc từ chối chuyến trước khi nghỉ nhận chuyến.',
  'Version conflict; read current trip before retry':'Chuyến đã được cập nhật ở nơi khác. Đang tải trạng thái mới; hãy kiểm tra trước khi thao tác lại.',
  'Invalid trip transition':'Thao tác không phù hợp với trạng thái hiện tại của chuyến.',
  'Trip access denied':'Tài khoản này không có quyền xem chuyến.', 'Expired token':'Phiên đăng nhập đã hết hạn.',
  'Invalid token':'Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.'
};
async function api(service, path, method = 'GET', data = undefined, user = session(), extra = {}) {
  const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 6500);
  try {
    const response = await fetch(`/api/${service}${path}`, {
      method,signal:controller.signal,cache:'no-store',
      headers:{'Content-Type':'application/json', ...(user ? {'Authorization':`Bearer ${user.token}`} : {}), ...extra},
      ...(data !== undefined ? {body:JSON.stringify(data)} : {})
    });
    const result = await response.json();
    if (!response.ok) {
      if (response.status === 401 && user && service !== 'identity') {
        if (state.sessions[user.role]?.id === user.id) {
          delete state.sessions[user.role]; persist(); renderAccount();
        }
      }
      const e = new Error(errorTranslations[result.error] || `Không thể thực hiện: ${result.error || response.status}`);
      e.status = response.status; throw e;
    }
    return result;
  } catch (e) {
    if (e.name === 'AbortError') throw new Error('Kết nối quá thời gian chờ. Kiểm tra trạng thái chuyến trước khi thử lại.');
    if (e instanceof TypeError) throw new Error('Không kết nối được ứng dụng. Kiểm tra terminal đang chạy hệ thống.');
    throw e;
  } finally { clearTimeout(timer); }
}
function coords(kind) { return [Number($(`#${kind}-lat`).value),Number($(`#${kind}-lon`).value)]; }
function setCoords(kind, point) { $(`#${kind}-lat`).value = point[0].toFixed(5); $(`#${kind}-lon`).value = point[1].toFixed(5); }
const addressFields={};
const normalizeSearch=value=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').replace(/Đ/g,'D').toLowerCase();
function chooseAddress(kind,place){
  const field=addressFields[kind];
  if(!field||!validPoint(place.location))return;
  field.seq++;clearTimeout(field.timer);if(field.controller)field.controller.abort();
  field.selected=true;field.input.value=place.name;field.input.setCustomValidity('');
  field.caption.textContent=place.address||place.location.map(n=>n.toFixed(5)).join(', ');
  field.caption.title=field.caption.textContent;
  if(kind==='pickup'){
    const area=place.area||['TP. Hồ Chí Minh','Hà Nội','Đà Nẵng','Cần Thơ','Nha Trang','Đà Lạt','Huế','Hội An','Vũng Tàu'].find(city=>place.name.includes(city))||
      (place.name.includes('demo')||places.slice(0,6).some(p=>p[0]===place.name)?'TP. Hồ Chí Minh':'Vị trí đã chọn');
    $('#service-area-label').textContent=area;$('#booking-area-label').textContent=area;
  }
  setCoords(kind,place.location);field.results.hidden=true;field.input.setAttribute('aria-expanded','false');
  $(`#${kind}-place`).value=String(places.length-1);estimate();renderBookingButton();
}
function setupAddressSearch(kind){
  const select=$(`#${kind}-place`),container=select.closest('.location-field');select.hidden=true;
  const input=document.createElement('input');input.type='text';input.id=kind+'-address';input.className='address-input';
  input.placeholder=kind==='pickup'?'Nhập điểm đón':'Nhập địa chỉ hoặc nơi bạn muốn đến';
  input.autocomplete='off';input.maxLength=160;input.required=true;
  input.setAttribute('role','combobox');input.setAttribute('aria-autocomplete','list');input.setAttribute('aria-expanded','false');
  input.setAttribute('aria-label',kind==='pickup'?'Tìm địa chỉ điểm đón':'Tìm địa chỉ điểm đến');
  const caption=document.createElement('p');caption.className='address-caption';
  const results=document.createElement('div');results.className='address-results';results.id=kind+'-results';results.hidden=true;
  input.setAttribute('aria-controls',kind+'-options');
  select.before(input);container.querySelector('.coordinate-details').before(caption,results);
  const field={input,caption,results,selected:true,seq:0,timer:null,controller:null,options:[],active:-1};addressFields[kind]=field;
  const catalog=query=>{
    const words=normalizeSearch(query).trim().split(/\s+/).filter(Boolean);
    return places.filter(p=>p[1]!==null&&words.every(w=>normalizeSearch(p[0]).includes(w))).slice(0,8)
      .map(p=>({name:p[0],location:[p[1],p[2]],address:'Địa điểm có sẵn · Vị trí tham khảo',source:'catalog'}));
  };
  const show=(options,message)=>{
    field.options=options;field.active=-1;
    results.innerHTML=`<div class="address-result-heading">${esc(message)}</div><div id="${kind}-options" role="listbox" aria-label="Địa điểm gợi ý">${options.map((p,i)=>`<button type="button" class="address-option" role="option" id="${kind}-option-${i}" aria-selected="false" data-address-index="${i}"><span class="address-result-icon">${icon('pin')}</span><span><strong>${esc(p.name)}</strong><small>${esc(p.address)}</small></span></button>`).join('')}</div><button type="button" class="address-search-more">Tìm địa chỉ trên bản đồ</button><div class="address-attribution">Tìm kiếm: Photon · © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a></div>`;
    results.hidden=document.activeElement!==input;input.setAttribute('aria-expanded',String(!results.hidden));input.removeAttribute('aria-activedescendant');
  };
  const search=async()=>{
    const query=input.value.trim();if(query.length<3||field.selected)return;
    const seq=++field.seq;const local=catalog(query);
    if(field.controller)field.controller.abort();field.controller=new AbortController();
    const timer=setTimeout(()=>field.controller?.abort(),6500);
    show(local,'Đang tìm địa chỉ…');
    try{
      const bias=coords('pickup');const params=new URLSearchParams({q:query,lat:bias[0],lon:bias[1]});
      const response=await fetch('/api/places/search?'+params,{signal:field.controller.signal,cache:'no-store'});
      if(!response.ok)throw new Error(response.status===429?'busy':'offline');
      const data=await response.json();
      if(seq!==field.seq||input.value.trim()!==query)return;
      const remote=(data.places||[]).filter(p=>typeof p.name==='string'&&Array.isArray(p.location)&&validPoint(p.location));
      const seen=new Set();const options=[...remote,...local].filter(p=>{const key=p.location.map(n=>n.toFixed(4)).join(',');if(seen.has(key))return false;seen.add(key);return true;}).slice(0,10);
      show(options,options.length?'Chọn đúng địa chỉ bên dưới':'Không tìm thấy. Thử thêm số nhà, quận hoặc thành phố.');
      field.caption.textContent=options.length?'Chọn một kết quả để xác nhận vị trí.':'Bạn có thể chọn trên bản đồ hoặc nhập tọa độ.';
    }catch(e){
      if(seq!==field.seq||input.value.trim()!==query)return;
      show(local,e.message==='busy'?'Tìm kiếm đang bận. Chờ một chút rồi thử lại.':'Chưa kết nối được tìm kiếm. Dùng địa điểm có sẵn hoặc tọa độ.');
    }finally{clearTimeout(timer);}
  };
  input.addEventListener('focus',()=>show(catalog(field.selected?'':input.value),'Địa điểm gợi ý · Có thể gõ địa chỉ bất kỳ'));
  input.addEventListener('input',()=>{
    field.seq++;field.selected=false;clearTimeout(field.timer);field.controller?.abort();
    input.setCustomValidity('Hãy chọn một kết quả địa chỉ để xác nhận vị trí.');
    caption.textContent='Chọn kết quả gợi ý để xác nhận vị trí.';renderBookingButton();
    const raw=input.value.trim();const coordinate=raw.match(/^(-?\d+(?:\.\d+)?)\s*[,;]\s*(-?\d+(?:\.\d+)?)$/);
    if(coordinate&&validPoint([+coordinate[1],+coordinate[2]])){
      show([{name:raw,location:[+coordinate[1],+coordinate[2]],address:'Tọa độ bạn nhập',source:'coordinates'}],'Chọn để sử dụng tọa độ này');return;
    }
    show(catalog(raw),raw.length<3?'Nhập ít nhất 3 ký tự để tìm địa chỉ trực tuyến':'Đang chờ tìm kiếm…');
    if(raw.length>=3)field.timer=setTimeout(search,900);
  });
  results.addEventListener('pointerdown',event=>{if(event.target.closest('button'))event.preventDefault();});
  results.addEventListener('click',event=>{
    const option=event.target.closest('[data-address-index]');
    if(option){chooseAddress(kind,field.options[Number(option.dataset.addressIndex)]);input.focus();results.hidden=true;input.setAttribute('aria-expanded','false');}
    if(event.target.closest('.address-search-more')){field.selected=false;clearTimeout(field.timer);search();}
  });
  input.addEventListener('keydown',event=>{
    if(event.key==='Escape'){results.hidden=true;input.setAttribute('aria-expanded','false');return;}
    if(event.key==='Enter'){
      event.preventDefault();
      if(!results.hidden&&field.active>=0)chooseAddress(kind,field.options[field.active]);
      else if(!field.selected){clearTimeout(field.timer);search();}
      return;
    }
    if(['ArrowDown','ArrowUp'].includes(event.key)&&field.options.length){
      event.preventDefault();field.active=(field.active+(event.key==='ArrowDown'?1:-1)+field.options.length)%field.options.length;
      results.querySelectorAll('[role="option"]').forEach((el,i)=>el.setAttribute('aria-selected',String(i===field.active)));
      input.setAttribute('aria-activedescendant',`${kind}-option-${field.active}`);
      results.querySelector(`#${kind}-option-${field.active}`)?.scrollIntoView({block:'nearest'});
    }
  });
  input.addEventListener('blur',()=>setTimeout(()=>{if(!container.contains(document.activeElement)){results.hidden=true;input.setAttribute('aria-expanded','false');}},180));
  const p=places[kind==='pickup'?1:2];chooseAddress(kind,{name:p[0],location:[p[1],p[2]],address:'Địa điểm có sẵn · Vị trí tham khảo'});
}
function validPoint(point) { return point.every(Number.isFinite) && Math.abs(point[0]) <= 90 && Math.abs(point[1]) <= 180; }
function distance(a,b) {
  const r = Math.PI / 180, dlat = (b[0]-a[0])*r, dlon = (b[1]-a[1])*r;
  const h = Math.sin(dlat/2)**2 + Math.cos(a[0]*r)*Math.cos(b[0]*r)*Math.sin(dlon/2)**2;
  return 12742*Math.asin(Math.min(1,Math.sqrt(h)));
}
function estimate() {
  const a=coords('pickup'),b=coords('destination'); if (!validPoint(a) || !validPoint(b)) return;
  const km=distance(a,b); $('#fare-label').textContent=money(12000+Math.round(km*8000));
  $('#distance-label').textContent=km.toFixed(2)+' km · Ước tính'; renderMap();
  refreshQuote();
}
let lastQuoteKey='',lastQuoteTime=0,quoteSeq=0;
async function refreshQuote(){
  const user=session();if(!user||user.role!=='passenger'||state.trips.some(t=>!terminal.has(t.state)))return;
  const pickup=coords('pickup'),destination=coords('destination');
  if(!validPoint(pickup)||!validPoint(destination)||Object.values(addressFields).some(f=>!f.selected))return;
  const fingerprint=JSON.stringify([user.id,pickup,destination]);
  if(fingerprint===lastQuoteKey&&Date.now()-lastQuoteTime<15000)return;
  lastQuoteKey=fingerprint;lastQuoteTime=Date.now();const seq=++quoteSeq;
  try{const quote=await api('pricing','/quote','POST',{pickup,destination},user);
    if(seq!==quoteSeq||session()?.id!==user.id)return;
    $('#fare-label').textContent=money(quote.fare);
    $('#distance-label').textContent=quote.distance_km+' km · Hệ số giá ×'+quote.multiplier+(quote.degraded_dependencies.length?' · Giá cơ bản':'' );
  }catch{/* Base estimate stays visible; booking itself requires a confirmed server-side quote. */}
}
function badge(status) { return `<span class="badge ${status==='completed'?'green':(['cancelled','payment_failed'].includes(status)?'red':'orange')}">${esc(labels[status] || status)}</span>`; }
function empty(title,message,kind='route') { return `<div class="empty-state">${icon(kind)}<strong>${esc(title)}</strong>${esc(message)}</div>`; }
function currentTrip() {
  return state.trips.find(t => !terminal.has(t.state)) || state.trips.find(t => t.id === state.selected) || state.trips[0];
}
function renderAccount() {
  const user=session(); $('#auth-panel').hidden=!state.authOpen; $('#signed-in-bar').hidden=!user; $('#logout').hidden=!user;$('#login-open').hidden=!!user;
  $('#account-pill').innerHTML=`<span class="avatar">${user ? esc(user.username.slice(0,1).toUpperCase()) : 'G'}</span><div><strong>${user ? esc(user.username) : 'Chào bạn!'}</strong><small>${user ? (state.role==='driver'?'Tài xế':'Hành khách') : 'Chưa đăng nhập'}</small></div>`;
  $('#role-switch').innerHTML=Object.entries(state.sessions).map(([role,u])=>`<button data-role="${esc(role)}" class="${state.role===role?'selected':''}">${icon(role==='driver'?'car':'user')}${role==='driver'?'Tài xế':'Hành khách'} · ${esc(u.username)}</button>`).join('') + '<button data-add-account="true">+ Thêm tài khoản</button>';
  $('#passenger-card').hidden=!!user && state.role==='driver'; $('#driver-card').hidden=!user || state.role!=='driver';
  renderBookingButton();
}
function renderBookingButton() {
  const active=state.trips.some(t=>!terminal.has(t.state));
  const unresolved=Object.values(addressFields).some(f=>!f.selected);
  $('#book-button').disabled=state.busy || state.demo || unresolved || (!!session() && (state.role!=='passenger' || active));
  $('#book-button').querySelector('span:nth-child(2)').textContent=state.busy?'Đang gửi yêu cầu…':active?'Bạn đang có chuyến':unresolved?'Chọn địa chỉ trong gợi ý':'Đặt xe ngay';
  $('#demo-setup').disabled=state.busy || state.demo;
  $('#demo-run').disabled=state.busy || state.demo;
}
function setView(view) {
  if (!['ride','history','payments','notifications','system'].includes(view)) view='ride';
  state.view=view; $$('.view').forEach(el=>{el.hidden=el.id!==`view-${view}`;});
  $$('.nav-item[data-view]').forEach(el=>el.classList.toggle('active',el.dataset.view===view));
  const titles={ride:['Bạn muốn đi đâu?','Chọn điểm đón và điểm đến để đặt xe.','Đặt xe'],history:['Lịch sử chuyến đi','Xem lại những chuyến xe của bạn.','Lịch sử'],payments:['Thanh toán','Lịch sử giao dịch và số tiền đã thanh toán.','Thanh toán'],notifications:['Thông báo','Cập nhật về chuyến đi của bạn.','Thông báo'],system:['Trạng thái hệ thống','Kết nối đến các dịch vụ của ứng dụng.','Hệ thống']};
  let [title,subtitle,breadcrumb]=titles[view];
  if (view==='ride' && session()?.role==='driver') {title='Nhận chuyến';subtitle='Bật nhận chuyến để bắt đầu làm việc.';}
  $('#page-title').textContent=title; $('#page-subtitle').textContent=subtitle; $('#breadcrumb-title').textContent=breadcrumb;
}
function renderTrip() {
  const trip=currentTrip();
  if (!session() || !trip) {
    $('#journey-title').textContent=state.role==='driver'&&session()?'Chưa có yêu cầu mới':'Chuyến đi của bạn';
    $('#trip-badge').textContent='Chưa có chuyến';$('#trip-badge').className='badge';
    $('#trip-detail').innerHTML=`<div class="empty-journey"><span class="empty-icon">${icon('route')}</span><p>${state.role==='driver'&&session()?'Bật nhận chuyến để nhận yêu cầu mới.':'Sau khi đặt xe, bạn có thể theo dõi tài xế và chuyến đi tại đây.'}</p></div>`;return;
  }
  $('#journey-title').textContent=`Chuyến #${shortId(trip.id)}`;
  $('#trip-badge').outerHTML=badge(trip.state).replace('class="badge ','id="trip-badge" class="badge ');
  const steps=['requested','offered','accepted','in_progress','completed'];
  const stepNames=['Đặt xe','Ghép tài xế','Đón khách','Di chuyển','Hoàn tất'];
  const index=trip.state==='awaiting_payment'?3:steps.indexOf(trip.state);
  const messages={requested:'Đang tìm tài xế phù hợp trong khu vực. Bạn có thể hủy trong lúc chờ.',offered:'Đã giữ tài xế cho chuyến này. Tài xế cần chấp nhận đề nghị.',accepted:'Tài xế đã nhận chuyến và đang đến điểm đón.',in_progress:'Chuyến đi đã bắt đầu. Chúc bạn một hành trình thoải mái!',awaiting_payment:'Chuyến đã kết thúc. Dịch vụ thanh toán đang xử lý; trạng thái sẽ tự cập nhật khi có kết quả.',completed:'Chuyến đi và thanh toán đã hoàn tất. Cảm ơn bạn đã đồng hành!',cancelled:'Chuyến đã kết thúc mà không thực hiện. Có thể do người dùng hủy, tài xế từ chối, không có xe phù hợp hoặc quá thời gian chờ.',payment_failed:'Chuyến đã kết thúc nhưng thanh toán mô phỏng bị từ chối. Hệ thống giải phóng tài xế và giữ lại lịch sử giao dịch.'};
  let actions='';
  if (state.role==='passenger' && ['requested','offered','accepted'].includes(trip.state)) actions='<button class="button danger" data-action="cancel">Hủy chuyến</button>';
  if (state.role==='driver') {
    if (trip.state==='offered') actions='<button class="button primary" data-action="accept">Chấp nhận chuyến</button><button class="button danger" data-action="reject">Từ chối</button>';
    if (trip.state==='accepted') actions='<button class="button primary" data-action="start">Đã đón khách · Bắt đầu</button>';
    if (trip.state==='in_progress') actions='<button class="button primary" data-action="complete">Hoàn thành chuyến</button>';
  }
  $('#trip-detail').innerHTML=`<div class="trip-meta"><span>Giá cước <strong>${money(trip.fare)}</strong></span><span>Tài xế <strong>${shortId(trip.driver_id)}</strong></span><span>${date(trip.created)}</span></div><div class="timeline">${steps.map((s,i)=>`<div class="timeline-item ${index>=i?'done':''} ${index===i?'current':''}"><i>${index>i?'✓':''}</i>${stepNames[i]}</div>`).join('')}</div><p class="trip-message">${esc(messages[trip.state] || trip.state)}</p><div class="trip-actions">${actions}</div><details class="trip-technical"><summary>Chi tiết chuyến</summary><p class="detail-code">Mã theo dõi: ${esc(trip.correlation_id)} · Phiên bản ${trip.version}</p></details>`;
  $$('#trip-detail [data-action]').forEach(el=>el.disabled=state.busy||state.demo);
}
function renderDriver() {
  const profile=state.driver;
  const names={available:'Đang nhận chuyến',offline:'Đang nghỉ',busy:'Đang có chuyến'};
  $('#driver-status-label').textContent=profile?(names[profile.status]||profile.status):'Chưa bật nhận chuyến';
  $('#driver-dot').classList.toggle('offline',!profile||profile.status==='offline');
  $('#driver-updated').textContent=profile?date(profile.updated):'';
  $('#driver-online').textContent=profile?.status==='busy'?'Cập nhật vị trí':'Bắt đầu nhận chuyến';
  $('#driver-offline').disabled=state.busy||state.demo||profile?.status==='busy';
  $('#driver-online').disabled=state.busy||state.demo;
}
function renderHistory() {
  $('#history-content').innerHTML=!session()?empty('Đăng nhập để xem lịch sử','Các chuyến đi của bạn sẽ được lưu tại đây.','clock'):!state.trips.length?empty('Chưa có chuyến đi','Chuyến đầu tiên của bạn đang ở phía trước.','clock'):`<div class="table-wrap"><table><thead><tr><th>CHUYẾN ĐI</th><th>THỜI GIAN</th><th>ĐIỂM ĐÓN → ĐIỂM ĐẾN</th><th>GIÁ CƯỚC</th><th>TRẠNG THÁI</th></tr></thead><tbody>${state.trips.map(t=>`<tr><td><button class="table-link" data-trip="${esc(t.id)}">#${shortId(t.id)}</button></td><td>${date(t.created)}</td><td>${t.pickup.map(n=>n.toFixed(3)).join(', ')}<br>→ ${t.destination.map(n=>n.toFixed(3)).join(', ')}</td><td>${money(t.fare)}</td><td>${badge(t.state)}</td></tr>`).join('')}</tbody></table></div>`;
}
function renderPayments() {
  const paid=state.payments.filter(p=>p.state==='paid');
  $('#payment-summary').innerHTML=[['Tổng thanh toán thành công',money(paid.reduce((s,p)=>s+p.amount,0))],['Giao dịch thành công',String(paid.length)],['Giao dịch bị từ chối',String(state.payments.filter(p=>p.state==='declined').length)]].map(([label,value])=>`<div class="summary-card"><p>${label}</p><strong>${value}</strong></div>`).join('');
  $('#payments-content').innerHTML=!session()?empty('Đăng nhập để xem giao dịch','Không có giao dịch tiền thật trong hệ thống này.','wallet'):!state.payments.length?empty('Chưa có thanh toán','Giao dịch xuất hiện khi một chuyến xe hoàn tất.','wallet'):`<div class="table-wrap"><table><thead><tr><th>CHUYẾN</th><th>THỜI GIAN</th><th>SỐ TIỀN</th><th>KẾT QUẢ</th></tr></thead><tbody>${state.payments.map(p=>`<tr><td><button class="table-link" data-trip="${esc(p.trip_id)}">#${shortId(p.trip_id)}</button></td><td>${date(p.created)}</td><td>${money(p.amount)}</td><td><span class="badge ${p.state==='paid'?'green':'red'}">${p.state==='paid'?'Thành công':'Bị từ chối'}</span></td></tr>`).join('')}</tbody></table></div>`;
}
function renderNotices() {
  $('#notice-count').textContent=state.notices.length;$('#bell-dot').hidden=!state.notices.length;
  $('#notifications-content').innerHTML=!session()?empty('Đăng nhập để nhận thông báo','Cập nhật hành trình sẽ được gửi đến đúng tài khoản của bạn.','bell'):!state.notices.length?empty('Bạn đã cập nhật mọi thứ','Thông báo mới sẽ xuất hiện khi có hoạt động.','bell'):state.notices.map(n=>`<div class="notice-item"><span class="soft-icon">${icon(n.topic.startsWith('payment')?'wallet':'bell')}</span><div><strong>${esc(topicLabels[n.topic] || n.topic)}</strong><p>Chuyến #${shortId(n.trip_id)} <button class="table-link" data-trip="${esc(n.trip_id)}">Xem hành trình</button></p></div><time>${date(n.timestamp)}</time></div>`).join('');
}
function render() {renderAccount();renderTrip();renderDriver();renderHistory();renderPayments();renderNotices();renderMap();setView(state.view);refreshQuote();}
async function refresh(showErrors=false) {
  const user=session();if(!user){state.trips=[];state.payments=[];state.notices=[];state.driver=null;render();return;}
  const nonce=++state.nonce;
  const requests=[api('trip','/trips','GET',undefined,user),api('payment','/payments','GET',undefined,user),api('notification','/notifications','GET',undefined,user)];
  if(user.role==='driver') requests.push(api('driver','/drivers/me','GET',undefined,user));
  const results=await Promise.allSettled(requests);
  if(nonce!==state.nonce||session()?.id!==user.id)return;
  for(let i=0;i<results.length;i++){
    const result=results[i];
    if(result.status==='fulfilled'){
      if(i===0)state.trips=result.value.trips;if(i===1)state.payments=result.value.payments;if(i===2)state.notices=result.value.notifications;
      if(i===3){state.driver=result.value;if(state.driverProfileUser!==user.id){setCoords('driver',result.value.location);state.driverProfileUser=user.id;}}
    }else if(showErrors && !(i===3&&result.reason.status===404)){toast(result.reason.message,true);}
  }
  if(!session()){state.trips=[];state.payments=[];state.notices=[];state.driver=null;}
  render();
}
async function refreshStatus() {
  try {
    const response=await fetch('/api/status',{cache:'no-store',signal:AbortSignal.timeout(4500)});
    if(!response.ok)throw new Error('status');state.services=(await response.json()).services;
    const up=Object.values(state.services).filter(s=>s.status==='up').length;
    const total=Object.keys(state.services).length;
    $('#connection-label').textContent=`${up}/${total} dịch vụ kết nối`;
    $('#sidebar-health').classList.toggle('offline',up<total);
    $('.live-label .status-dot').classList.toggle('offline',up<total);
  }catch{$('#connection-label').textContent='Mất kết nối';$('#sidebar-health').classList.add('offline');}
  const descriptions={identity:['Tài khoản','Đăng ký, đăng nhập và phân quyền'],driver:['Tài xế','Vị trí, trạng thái và giữ tài xế'],trip:['Chuyến đi','Đặt xe và vòng đời hành trình'],matching:['Ghép chuyến','Kết nối tài xế phù hợp'],payment:['Thanh toán','Xử lý giao dịch mô phỏng'],notification:['Thông báo','Cập nhật cho hai bên'],broker:['Hàng đợi','Chuyển sự kiện bất đồng bộ'],pricing:['Giá cước','Báo giá và giá theo nhu cầu'],observability:['Giám sát','Log tập trung và trace']};
  $('#service-grid').innerHTML=Object.entries(descriptions).map(([name,[title,description]])=>{const up=state.services[name]?.status==='up';return `<div class="service-card"><div class="service-title"><h3>${title}</h3><span class="badge ${up?'green':'red'}">${up?'Đang hoạt động':'Mất kết nối'}</span></div><p>${description}</p><small>${name}</small></div>`;}).join('');
}
async function perform(fn) {if(state.busy)return;state.busy=true;renderBookingButton();renderDriver();try{await fn();}catch(e){toast(e.message,true);}finally{state.busy=false;await refresh();}}
async function changeRole(role) {if(!state.sessions[role]||state.demo)return;state.nonce++;state.role=role;state.selected=null;state.trips=[];state.payments=[];state.notices=[];state.driver=null;persist();render();await refresh(true);}
async function tripAction(action) {
  if(state.demo)return;
  const trip=currentTrip();if(!trip)return;
  if(['cancel','reject'].includes(action)&&!window.confirm(action==='cancel'?'Bạn muốn hủy chuyến này?':'Bạn muốn từ chối chuyến này?'))return;
  await perform(async()=>{
    const updated=await api('trip',`/trips/${trip.id}/${action}`,'POST',{version:trip.version});
    state.selected=updated.id;toast(labels[updated.state]);
  });
}
async function updateDriver(offline=false,quiet=false) {
  const point=coords('driver');if(!validPoint(point))throw new Error('Tọa độ tài xế không hợp lệ.');
  const user=state.sessions.driver;if(!user)throw new Error('Hãy đăng nhập tài khoản tài xế.');
  const status=offline?'offline':(state.driver?.active_trip?'busy':'available');
  await api('driver','/drivers/me','POST',{location:point,status},user);state.lastHeartbeat=Date.now();
  if(!quiet)toast(offline?'Đã nghỉ nhận chuyến.':'Đã cập nhật trạng thái và vị trí.');
}
async function waitFor(fn,predicate,seconds=25) {const end=Date.now()+seconds*1000;while(Date.now()<end){const value=await fn();if(predicate(value))return value;await new Promise(resolve=>setTimeout(resolve,450));}throw new Error('Chưa nhận được kết quả sau thời gian chờ. Kiểm tra hành trình và các dịch vụ; yêu cầu vẫn có thể tiếp tục được xử lý.');}
async function setupDemo() {
  // Public registration endpoints create real accounts; generated passwords never leave memory/storage logs.
  const suffix=crypto.randomUUID().replaceAll('-','').slice(0,10), password=crypto.randomUUID()+'!';
  const passenger=await api('identity','/register','POST',{username:'khach_'+suffix,password,role:'passenger'},null);
  const driver=await api('identity','/register','POST',{username:'taixe_'+suffix,password,role:'driver'},null);
  state.sessions={passenger,driver};state.role='passenger';state.selected=null;state.authOpen=false;
  state.trips=[];state.payments=[];state.notices=[];state.driver=null;state.pendingBooking=null;
  const point=[10.7769+Math.random()*.006,106.7009+Math.random()*.006];
  chooseAddress('pickup',{name:'Điểm đón demo',location:point,address:'Vị trí tài xế demo'});setCoords('driver',point);
  chooseAddress('destination',{name:'Thảo Cầm Viên',location:[10.7900,106.7200],address:'TP. Hồ Chí Minh'});
  await api('driver','/drivers/me','POST',{location:coords('driver'),status:'available'},driver);
  state.lastHeartbeat=Date.now();persist();estimate();setView('ride');
}
function demoStep(index,status) {state.demoSteps[index]=status;$('#demo-steps').innerHTML=['Tài khoản & tài xế','Đặt xe','Ghép tài xế','Chấp nhận','Bắt đầu','Hoàn tất','Thanh toán'].map((label,i)=>`<span class="demo-step ${state.demoSteps[i]||''}"><span>${state.demoSteps[i]==='done'?'✓':i+1}</span>${label}</span>`).join('');}
async function runDemo() {
  if(state.busy||state.demo)return;
  if(session()&&state.trips.some(t=>!terminal.has(t.state))){toast('Hãy kết thúc chuyến hiện tại trước khi chạy demo mới.',true);return;}
  state.demo=true;state.demoSteps=[];$('#demo-progress').hidden=false;$('#demo-badge').textContent='Đang chạy';
  $('#demo-message').textContent='Các thao tác dưới đây đang thực hiện qua dịch vụ thật. Bạn có thể chuyển màn hình sau khi demo hoàn tất.';
  setView('ride');renderBookingButton();let index=0;
  try {
    demoStep(index,'running');await setupDemo();demoStep(index++,'done');await refresh();
    demoStep(index,'running');
    const user=state.sessions.passenger,driver=state.sessions.driver;
    let trip=await api('trip','/trips','POST',{pickup:coords('pickup'),destination:coords('destination'),payment_mode:$('#payment-mode').value},user,{'Idempotency-Key':crypto.randomUUID()});
    state.selected=trip.id;demoStep(index++,'done');await refresh();
    demoStep(index,'running');trip=await waitFor(()=>api('trip','/trips/'+trip.id,'GET',undefined,user),t=>t.state==='offered'||terminal.has(t.state));
    if(trip.state!=='offered')throw new Error('Không thể ghép tài xế cho chuyến demo. Hãy kiểm tra dịch vụ và thử lại.');
    if(trip.driver_id!==driver.id)throw new Error('Chuyến được gán cho một tài xế đang online khác. Hãy chuyển sang tài khoản tài xế đó để nhận chuyến, hoặc hủy rồi chuẩn bị demo mới.');
    demoStep(index++,'done');await refresh();
    for(const action of ['accept','start','complete']){
      demoStep(index,'running');await new Promise(resolve=>setTimeout(resolve,1200));
      trip=await api('trip',`/trips/${trip.id}/${action}`,'POST',{version:trip.version},driver);
      demoStep(index++,'done');await refresh();
    }
    demoStep(index,'running');await waitFor(()=>api('trip','/trips/'+trip.id,'GET',undefined,user),t=>terminal.has(t.state));
    demoStep(index,'done');$('#demo-badge').textContent='Đã hoàn tất';
    $('#demo-message').textContent='Chuyến mẫu đã hoàn tất. Mở Lịch sử, Thanh toán hoặc Thông báo để xem dữ liệu; chuyển sang Tài xế để khám phá màn hình nhận chuyến.';
    toast('Demo hoàn tất! Dữ liệu đã được lưu ở các dịch vụ.');
  } catch(e){demoStep(index,'failed');$('#demo-badge').textContent='Cần kiểm tra';$('#demo-message').textContent=e.message;toast(e.message,true);}
  finally{state.demo=false;renderBookingButton();await refresh(true);}
}

function renderMap() {
  const current=session()?currentTrip():null;
  const trip=current&&(state.role==='driver'||!terminal.has(current.state))?current:null;
  const pickup=trip?.pickup||coords('pickup'),destination=trip?.destination||coords('destination');
  if(!validPoint(pickup)||!validPoint(destination))return;
  const driver=state.driver?.location||(state.sessions.driver&&state.lastHeartbeat?coords('driver'):null);
  window.GoRideMap.update({pickup,destination,driver:driver&&validPoint(driver)?driver:null});
}

// Forms and navigation are wired once; polling only updates data containers.
hydrateIcons();
for(const kind of ['pickup','destination']){
  const select=$(`#${kind}-place`);select.innerHTML=places.map(([name],i)=>`<option value="${i}">${name}</option>`).join('');select.value=kind==='pickup'?'1':'2';
  select.addEventListener('change',()=>{const [name,lat,lon]=places[Number(select.value)];if(lat!==null)chooseAddress(kind,{name,location:[lat,lon],address:'Địa điểm có sẵn'});});
  setupAddressSearch(kind);
  for(const axis of ['lat','lon'])$(`#${kind}-${axis}`).addEventListener('input',()=>{
    const point=coords(kind);if(validPoint(point))chooseAddress(kind,{name:'Vị trí tùy chọn',location:point,address:point.join(', ')});else{addressFields[kind].selected=false;renderBookingButton();}
  });
}
document.addEventListener('click',async(event)=>{
  const target=event.target.closest('button,a');if(!target)return;
  if(target.dataset.view){setView(target.dataset.view);if(target.dataset.view==='system')refreshStatus();}
  if(target.dataset.role)await changeRole(target.dataset.role);
  if(target.dataset.addAccount&&!state.demo){state.authOpen=true;$('#auth-panel').hidden=false;$('#username').focus();}
  if(target.dataset.auth){state.authMode=target.dataset.auth;$$('[data-auth]').forEach(el=>el.classList.toggle('selected',el===target));$('#register-role').hidden=state.authMode!=='register';$('#auth-submit').textContent=state.authMode==='register'?'Tạo tài khoản':'Đăng nhập';$('#auth-title').textContent=state.authMode==='register'?'Tạo tài khoản GoRide':'Đăng nhập GoRide';$('#password').autocomplete=state.authMode==='register'?'new-password':'current-password';$('#auth-error').hidden=true;}
  if(target.dataset.action)await tripAction(target.dataset.action);
  if(target.dataset.trip){state.selected=target.dataset.trip;setView('ride');renderTrip();renderMap();}
  if(target.classList.contains('refresh-button'))await refresh(true);
  if(target.dataset.mapTarget){
    if(!window.GoRideMap.canSelect()){toast('Chuyến đang hoạt động. Bạn không thể đổi vị trí của chuyến này.',true);return;}
    const kind=target.dataset.mapTarget;
    if(!window.GoRideMap.setTarget(kind)){toast('Bản đồ chưa tải xong. Kiểm tra kết nối Internet và thử lại.',true);return;}
    state.mapTarget=kind;$$('[data-map-target]').forEach(el=>el.classList.toggle('active',el===target));
    $('#map-instruction').textContent='Bấm trên bản đồ để chọn '+(kind==='pickup'?'điểm đón':'điểm đến');
    $('#ride-map').scrollIntoView({behavior:'smooth',block:'center'});
  }
});
$('#auth-form').addEventListener('submit',async(event)=>{
  event.preventDefault();$('#auth-error').hidden=true;$('#auth-submit').disabled=true;
  try {
    const user=await api('identity','/'+state.authMode,'POST',{username:$('#username').value,password:$('#password').value,role:$('#auth-role').value},null);
    state.sessions[user.role]=user;state.role=user.role;state.selected=null;state.nonce++;state.trips=[];state.driver=null;state.pendingBooking=null;state.authOpen=false;
    $('#password').value='';persist();toast('Chào mừng '+user.username+'!');render();await refresh(true);
  }catch(e){$('#auth-error').textContent=e.message;$('#auth-error').hidden=false;}
  finally{$('#auth-submit').disabled=false;}
});
$('#toggle-password').addEventListener('click',()=>{const input=$('#password');input.type=input.type==='password'?'text':'password';$('#toggle-password').setAttribute('aria-label',input.type==='password'?'Hiện mật khẩu':'Ẩn mật khẩu');});
$('#logout').addEventListener('click',()=>{if(state.demo){toast('Đợi demo hoàn tất trước khi đăng xuất.',true);return;}delete state.sessions[state.role];state.nonce++;state.role=state.sessions.passenger?'passenger':'driver';state.trips=[];state.payments=[];state.notices=[];state.driver=null;state.selected=null;persist();render();refresh();});
$('#booking-form').addEventListener('submit',async(event)=>{
  event.preventDefault();if(state.demo)return;
  if(!session()){openAuth();toast('Đăng nhập tài khoản hành khách để đặt xe.');return;}
  if(state.role!=='passenger')return;
  await perform(async()=>{
    const data={pickup:coords('pickup'),destination:coords('destination'),payment_mode:$('#payment-mode').value};
    if(!validPoint(data.pickup)||!validPoint(data.destination))throw new Error('Vui lòng kiểm tra tọa độ điểm đón và điểm đến.');
    const fingerprint=JSON.stringify(data);
    if(state.pendingBooking?.fingerprint!==fingerprint||state.pendingBooking?.user!==session().id)state.pendingBooking={fingerprint,user:session().id,key:crypto.randomUUID()};
    persist();const trip=await api('trip','/trips','POST',data,session(),{'Idempotency-Key':state.pendingBooking.key});
    state.pendingBooking=null;persist();state.selected=trip.id;toast('Đã gửi yêu cầu. Đang tìm tài xế cho bạn.');
  });
});
$('#driver-form').addEventListener('submit',async(event)=>{event.preventDefault();await perform(()=>updateDriver());});
$('#driver-offline').addEventListener('click',()=>perform(()=>updateDriver(true)));
$('#driver-use-pickup').addEventListener('click',()=>{setCoords('driver',coords('pickup'));toast('Đã điền vị trí. Nhấn nút cập nhật để gửi.');});
$('#demo-setup').addEventListener('click',async()=>{
  $('.demo-menu').open=false;
  if(session()&&state.trips.some(t=>!terminal.has(t.state))){toast('Hãy kết thúc chuyến hiện tại trước khi tạo phiên demo mới.',true);return;}
  await perform(async()=>{await setupDemo();toast('Đã tạo hành khách và tài xế đang online. Bạn có thể đặt xe hoặc chuyển vai trò ở phía trên.');});
});
$('#demo-run').addEventListener('click',()=>{$('.demo-menu').open=false;runDemo();});
function openAuth(){state.authOpen=true;$('#auth-panel').hidden=false;$('#username').focus();}
function closeAuth(){state.authOpen=false;$('#auth-panel').hidden=true;$('#login-open').focus();}
$('#login-open').addEventListener('click',openAuth);
$('#auth-close').addEventListener('click',closeAuth);
document.addEventListener('keydown',event=>{
  if(!state.authOpen)return;
  if(event.key==='Escape'){closeAuth();return;}
  if(event.key==='Tab'){
    const focusable=[...$('#auth-panel').querySelectorAll('button,input,select')].filter(el=>!el.disabled&&el.getClientRects().length);
    const first=focusable[0],last=focusable[focusable.length-1];
    if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
    if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
  }
});
$('#map-reset').addEventListener('click',()=>window.GoRideMap.update(window.GoRideMap.latest,true));
window.GoRideMap.canSelect=()=>!state.demo&&!state.busy&&!(session()&&currentTrip()&&!terminal.has(currentTrip().state));
window.GoRideMap.onSelect=(kind,place)=>{chooseAddress(kind,place);state.mapTarget=null;$$('[data-map-target]').forEach(el=>el.classList.remove('active'));};
window.GoRideMap.init();
estimate();render();refreshStatus();refresh();
setInterval(async()=>{if(document.hidden||state.refreshing)return;state.refreshing=true;try{await refresh();}finally{state.refreshing=false;}},2000);
setInterval(()=>{if(!document.hidden)refreshStatus();},10000);
setInterval(async()=>{
  // Only send presence for the visibly active driver account; never re-enable an offline driver.
  if(document.hidden||state.role!=='driver'||!session()||state.busy||state.demo||!state.driver||state.driver.status==='offline'||Date.now()-state.lastHeartbeat<60000)return;
  try{await updateDriver(false,true);}catch{/* User-triggered refresh and status cards expose outages. */}
},15000);
