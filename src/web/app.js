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
function validPoint(point) { return point.every(Number.isFinite) && Math.abs(point[0]) <= 90 && Math.abs(point[1]) <= 180; }
function distance(a,b) {
  const r = Math.PI / 180, dlat = (b[0]-a[0])*r, dlon = (b[1]-a[1])*r;
  const h = Math.sin(dlat/2)**2 + Math.cos(a[0]*r)*Math.cos(b[0]*r)*Math.sin(dlon/2)**2;
  return 12742*Math.asin(Math.min(1,Math.sqrt(h)));
}
function estimate() {
  const a=coords('pickup'),b=coords('destination'); if (!validPoint(a) || !validPoint(b)) return;
  const km=distance(a,b); $('#fare-label').textContent=money(12000+Math.round(km*8000));
  $('#distance-label').textContent=km.toFixed(2)+' km · Khoảng cách mô phỏng'; renderMap();
}
function badge(status) { return `<span class="badge ${status==='completed'?'green':(['cancelled','payment_failed'].includes(status)?'red':'orange')}">${esc(labels[status] || status)}</span>`; }
function empty(title,message,kind='route') { return `<div class="empty-state">${icon(kind)}<strong>${esc(title)}</strong>${esc(message)}</div>`; }
function currentTrip() {
  return state.trips.find(t => !terminal.has(t.state)) || state.trips.find(t => t.id === state.selected) || state.trips[0];
}
function renderAccount() {
  const user=session(); $('#auth-panel').hidden=!!user&&!state.authOpen; $('#signed-in-bar').hidden=!user; $('#logout').hidden=!user;
  $('#account-pill').innerHTML=`<span class="avatar">${user ? esc(user.username.slice(0,1).toUpperCase()) : 'G'}</span><div><strong>${user ? esc(user.username) : 'Chào bạn!'}</strong><small>${user ? (state.role==='driver'?'Tài xế':'Hành khách') : 'Chưa đăng nhập'}</small></div>`;
  $('#role-switch').innerHTML=Object.entries(state.sessions).map(([role,u])=>`<button data-role="${esc(role)}" class="${state.role===role?'selected':''}">${icon(role==='driver'?'car':'user')}${role==='driver'?'Tài xế':'Hành khách'} · ${esc(u.username)}</button>`).join('') + '<button data-add-account="true">+ Thêm tài khoản</button>';
  $('#passenger-card').hidden=!!user && state.role==='driver'; $('#driver-card').hidden=!user || state.role!=='driver';
  renderBookingButton();
}
function renderBookingButton() {
  const active=state.trips.some(t=>!terminal.has(t.state));
  $('#book-button').disabled=state.busy || state.demo || (!!session() && (state.role!=='passenger' || active));
  $('#book-button').querySelector('span:nth-child(2)').textContent=state.busy?'Đang gửi yêu cầu…':active?'Bạn đang có chuyến':'Đặt xe ngay';
  $('#demo-setup').disabled=state.busy || state.demo;
  $('#demo-run').disabled=state.busy || state.demo;
}
function setView(view) {
  if (!['ride','history','payments','notifications','system'].includes(view)) view='ride';
  state.view=view; $$('.view').forEach(el=>{el.hidden=el.id!==`view-${view}`;});
  $$('.nav-item[data-view]').forEach(el=>el.classList.toggle('active',el.dataset.view===view));
  const titles={ride:['Đi đâu hôm nay?','Một chuyến đi thoải mái bắt đầu từ đây.','Chuyến đi'],history:['Những hành trình đã qua','Mỗi chuyến đi là một câu chuyện.','Lịch sử chuyến'],payments:['Thanh toán thật rõ ràng','Theo dõi giao dịch mô phỏng của bạn.','Thanh toán'],notifications:['Luôn kết nối với hành trình','Các cập nhật mới nhất dành cho bạn.','Thông báo'],system:['Mọi kết nối, trong tầm nhìn','Trạng thái hoạt động của các dịch vụ.','Hệ thống']};
  let [title,subtitle,breadcrumb]=titles[view];
  if (view==='ride' && session()?.role==='driver') {title='Sẵn sàng đón chuyến mới?';subtitle='Bật nhận chuyến và kết nối với hành khách gần bạn.';}
  $('#page-title').textContent=title; $('#page-subtitle').textContent=subtitle; $('#breadcrumb-title').textContent=breadcrumb;
}
function renderTrip() {
  const trip=currentTrip();
  if (!session() || !trip) {
    $('#journey-title').textContent=state.role==='driver'&&session()?'Chưa có yêu cầu mới':'Chuyến đi mới đang chờ bạn';
    $('#trip-badge').textContent='Chưa có chuyến';$('#trip-badge').className='badge';
    $('#trip-detail').innerHTML=`<div class="empty-journey"><span class="empty-icon">${icon('route')}</span><p>${state.role==='driver'&&session()?'Bật nhận chuyến để hành khách tìm thấy bạn.<br>Yêu cầu mới sẽ xuất hiện tự động tại đây.':'Chọn điểm đón và điểm đến để bắt đầu.<br>Trạng thái chuyến sẽ cập nhật tự động tại đây.'}</p></div>`;return;
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
  $('#trip-detail').innerHTML=`<div class="trip-meta"><span>Giá cước <strong>${money(trip.fare)}</strong></span><span>Tài xế <strong>${shortId(trip.driver_id)}</strong></span><span>${date(trip.created)}</span></div><div class="timeline">${steps.map((s,i)=>`<div class="timeline-item ${index>=i?'done':''} ${index===i?'current':''}"><i>${index>i?'✓':''}</i>${stepNames[i]}</div>`).join('')}</div><p class="trip-message">${esc(messages[trip.state] || trip.state)}</p><div class="trip-actions">${actions}</div><p class="detail-code">Mã theo dõi: ${esc(trip.correlation_id)} · Phiên bản ${trip.version}</p>`;
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
  $('#history-content').innerHTML=!session()?empty('Đăng nhập để xem lịch sử','Các chuyến đi của bạn sẽ được lưu tại đây.','clock'):!state.trips.length?empty('Chưa có chuyến đi','Chuyến đầu tiên của bạn đang ở phía trước.','clock'):`<div class="table-wrap"><table><thead><tr><th>CHUYẾN ĐI</th><th>THỜI GIAN</th><th>ĐIỂM ĐÓN → ĐIỂM ĐẾN</th><th>GIÁ CƯỚC</th><th>TRẠNG THÁI</th></tr></thead><tbody>${state.trips.map(t=>`<tr><td><button class="table-link" data-trip="${esc(t.id)}">#${shortId(t.id)} ↗</button></td><td>${date(t.created)}</td><td>${t.pickup.map(n=>n.toFixed(3)).join(', ')}<br>→ ${t.destination.map(n=>n.toFixed(3)).join(', ')}</td><td>${money(t.fare)}</td><td>${badge(t.state)}</td></tr>`).join('')}</tbody></table></div>`;
}
function renderPayments() {
  const paid=state.payments.filter(p=>p.state==='paid');
  $('#payment-summary').innerHTML=[['Tổng thanh toán thành công',money(paid.reduce((s,p)=>s+p.amount,0))],['Giao dịch thành công',String(paid.length)],['Giao dịch bị từ chối',String(state.payments.filter(p=>p.state==='declined').length)]].map(([label,value])=>`<div class="summary-card"><p>${label}</p><strong>${value}</strong></div>`).join('');
  $('#payments-content').innerHTML=!session()?empty('Đăng nhập để xem giao dịch','Không có giao dịch tiền thật trong hệ thống này.','wallet'):!state.payments.length?empty('Chưa có thanh toán','Giao dịch xuất hiện khi một chuyến xe hoàn tất.','wallet'):`<div class="table-wrap"><table><thead><tr><th>CHUYẾN</th><th>THỜI GIAN</th><th>SỐ TIỀN</th><th>KẾT QUẢ</th></tr></thead><tbody>${state.payments.map(p=>`<tr><td><button class="table-link" data-trip="${esc(p.trip_id)}">#${shortId(p.trip_id)} ↗</button></td><td>${date(p.created)}</td><td>${money(p.amount)}</td><td><span class="badge ${p.state==='paid'?'green':'red'}">${p.state==='paid'?'Thành công':'Bị từ chối'}</span></td></tr>`).join('')}</tbody></table></div>`;
}
function renderNotices() {
  $('#notice-count').textContent=state.notices.length;$('#bell-dot').hidden=!state.notices.length;
  $('#notifications-content').innerHTML=!session()?empty('Đăng nhập để nhận thông báo','Cập nhật hành trình sẽ được gửi đến đúng tài khoản của bạn.','bell'):!state.notices.length?empty('Bạn đã cập nhật mọi thứ','Thông báo mới sẽ xuất hiện khi có hoạt động.','bell'):state.notices.map(n=>`<div class="notice-item"><span class="soft-icon">${icon(n.topic.startsWith('payment')?'wallet':'bell')}</span><div><strong>${esc(topicLabels[n.topic] || n.topic)}</strong><p>Chuyến #${shortId(n.trip_id)} <button class="table-link" data-trip="${esc(n.trip_id)}">Xem hành trình ↗</button></p></div><time>${date(n.timestamp)}</time></div>`).join('');
}
function render() {renderAccount();renderTrip();renderDriver();renderHistory();renderPayments();renderNotices();renderMap();setView(state.view);}
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
    $('#connection-label').textContent=`${up}/7 dịch vụ kết nối`;
    $('#sidebar-health').classList.toggle('offline',up<7);
    $('.live-label .status-dot').classList.toggle('offline',up<7);
  }catch{$('#connection-label').textContent='Mất kết nối';$('#sidebar-health').classList.add('offline');}
  const descriptions={identity:['Tài khoản','Đăng ký, đăng nhập và phân quyền'],driver:['Tài xế','Vị trí, trạng thái và giữ tài xế'],trip:['Chuyến đi','Đặt xe và vòng đời hành trình'],matching:['Ghép chuyến','Kết nối tài xế phù hợp'],payment:['Thanh toán','Xử lý giao dịch mô phỏng'],notification:['Thông báo','Cập nhật cho hai bên'],broker:['Hàng đợi','Chuyển sự kiện bất đồng bộ']};
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
  setCoords('pickup',point);setCoords('driver',point);$('#pickup-place').value=String(places.length-1);
  setCoords('destination',[10.7900,106.7200]);$('#destination-place').value='2';
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
  const driver=state.driver?.location || (state.sessions.driver && state.lastHeartbeat ? coords('driver'):null);
  const points=[pickup,destination,...(driver&&validPoint(driver)?[driver]:[])];
  const lat=points.map(p=>p[0]),lon=points.map(p=>p[1]);
  let minLat=Math.min(...lat),maxLat=Math.max(...lat),minLon=Math.min(...lon),maxLon=Math.max(...lon);
  const latSpan=Math.max(.024,maxLat-minLat)*1.8,lonSpan=Math.max(.035,maxLon-minLon)*1.7;
  const midLat=(minLat+maxLat)/2,midLon=(minLon+maxLon)/2;
  const xy=p=>[450+(p[1]-midLon)/lonSpan*900,275-(p[0]-midLat)/latSpan*550];
  const [ax,ay]=xy(pickup),[bx,by]=xy(destination);
  const roads=`<path d="M-20 126 950 126M-20 212 950 212M-20 380 950 380M-20 478 950 478M105-20v600M260-20v600M445-20v600M590-20v600M790-20v600M-80 510 560-30M220 620 950 20" fill="none" stroke="#fffdf7" stroke-width="16"/><path d="M-20 126 950 126M-20 380 950 380M260-20v600M590-20v600M-80 510 560-30" fill="none" stroke="#e6dcc4" stroke-width="2"/>`;
  const marker=(x,y,kind,label)=>`<g transform="translate(${x} ${y})"><circle r="24" fill="${kind==='pickup'?'#6f9873':'#d89a73'}" opacity=".12"/><path d="M0 6C-20-8-13-25 0-25S20-8 0 6Z" fill="${kind==='pickup'?'#537f5a':'#d4946a'}" stroke="white" stroke-width="3"/><circle cy="-12" r="4" fill="white"/><rect x="-51" y="15" width="102" height="25" rx="6" fill="white" stroke="#e1e8d7"/><text y="32" text-anchor="middle" fill="#6f8561" font-size="10" font-family="Segoe UI,Arial">${label}</text></g>`;
  $('#ride-map').innerHTML=`<defs><pattern id="blocks" width="155" height="84" patternUnits="userSpaceOnUse"><rect x="10" y="8" width="130" height="65" rx="8" fill="#e7ecdf"/><path d="M15 15h45v22H15zm54 0h60v22H69zM15 44h75v20H15zm84 0h30v20H99z" fill="#e1e8d6" opacity=".6"/></pattern><filter id="marker-shadow"><feDropShadow dx="0" dy="3" stdDeviation="3" flood-opacity=".1"/></filter></defs><rect width="900" height="550" fill="#eff1e6"/><rect width="900" height="550" fill="url(#blocks)"/><path d="M760-60c-75 120 62 190 12 280S690 340 780 440s-15 130 7 170" fill="none" stroke="#c5dcd3" stroke-width="60"/><path d="M745-60c-75 120 62 190 12 280S675 340 765 440s-15 130 7 170" fill="none" stroke="#e0e9d8" stroke-width="5"/><rect x="290" y="235" width="120" height="115" rx="14" fill="#d6e5c7"/><rect x="111" y="140" width="129" height="55" rx="8" fill="#dbe8cd"/>${roads}<g fill="#acb49b" font-family="Segoe UI,Arial" font-size="10" letter-spacing="1"><text x="320" y="290" text-anchor="middle">CÔNG VIÊN</text><text x="497" y="100">TRUNG TÂM</text><text x="390" y="455">KHU DÂN CƯ</text><text x="600" y="355">BẾN SÔNG</text><text x="130" y="207" font-size="8">ĐƯỜNG PHỐ MINH HỌA</text></g><path d="M${ax} ${ay}Q${(ax+bx)/2+40} ${ay} ${bx} ${by}" stroke="#b0c4a5" stroke-width="10" opacity=".4" fill="none"/><path class="route-line" d="M${ax} ${ay}Q${(ax+bx)/2+40} ${ay} ${bx} ${by}" stroke="#77986b" stroke-width="3" fill="none"/><g filter="url(#marker-shadow)">${marker(ax,ay,'pickup','Điểm đón của bạn')}${marker(bx,by,'destination','Điểm đến')}</g>${driver?(()=>{const [x,y]=xy(driver);return `<g transform="translate(${x-21} ${y+25})"><rect width="42" height="25" rx="8" fill="#fff" stroke="#9cb38a"/><path d="m9 12 3-5h15l4 5v8H9zm4-1h14M14 16h.1m12 0h.1" stroke="#77956a" fill="none" stroke-width="1.5"/></g>`;})():''}`;
}

// Forms and navigation are wired once; polling only updates data containers.
hydrateIcons();
for(const kind of ['pickup','destination']){
  const select=$(`#${kind}-place`);select.innerHTML=places.map(([name],i)=>`<option value="${i}">${name}</option>`).join('');select.value=kind==='pickup'?'1':'2';
  select.addEventListener('change',()=>{const [,lat,lon]=places[Number(select.value)];if(lat!==null)setCoords(kind,[lat,lon]);estimate();});
  for(const axis of ['lat','lon'])$(`#${kind}-${axis}`).addEventListener('input',()=>{select.value=String(places.length-1);estimate();});
}
document.addEventListener('click',async(event)=>{
  const target=event.target.closest('button,a');if(!target)return;
  if(target.dataset.view){setView(target.dataset.view);if(target.dataset.view==='system')refreshStatus();}
  if(target.dataset.role)await changeRole(target.dataset.role);
  if(target.dataset.addAccount&&!state.demo){state.authOpen=true;$('#auth-panel').hidden=false;$('#username').focus();}
  if(target.dataset.auth){state.authMode=target.dataset.auth;$$('[data-auth]').forEach(el=>el.classList.toggle('selected',el===target));$('#register-role').hidden=state.authMode!=='register';$('#auth-submit').innerHTML=(state.authMode==='register'?'Tạo tài khoản':'Đăng nhập')+' <span>→</span>';$('#password').autocomplete=state.authMode==='register'?'new-password':'current-password';$('#auth-error').hidden=true;}
  if(target.dataset.action)await tripAction(target.dataset.action);
  if(target.dataset.trip){state.selected=target.dataset.trip;setView('ride');renderTrip();renderMap();}
  if(target.classList.contains('refresh-button'))await refresh(true);
  if(target.dataset.mapTarget){state.mapTarget=target.dataset.mapTarget;$$('[data-map-target]').forEach(el=>el.classList.toggle('active',el===target));$('#map-instruction').textContent='Nhấn trên sơ đồ để chọn '+(state.mapTarget==='pickup'?'điểm đón':'điểm đến');}
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
  if(!session()){$('#auth-panel').hidden=false;$('#username').focus();toast('Đăng nhập tài khoản hành khách để đặt xe.');return;}
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
  if(session()&&state.trips.some(t=>!terminal.has(t.state))){toast('Hãy kết thúc chuyến hiện tại trước khi tạo phiên demo mới.',true);return;}
  await perform(async()=>{await setupDemo();toast('Đã tạo hành khách và tài xế đang online. Bạn có thể đặt xe hoặc chuyển vai trò ở phía trên.');});
});
$('#demo-run').addEventListener('click',runDemo);
$('#map-reset').addEventListener('click',renderMap);
$('#ride-map').addEventListener('click',(event)=>{
  if(!state.mapTarget){toast('Chọn “Chọn trên sơ đồ” ở ô điểm đón hoặc điểm đến trước.');return;}
  if(session()&&currentTrip()&&!terminal.has(currentTrip().state)){toast('Chuyến đang hoạt động; tọa độ hành trình không thể thay đổi.',true);return;}
  const a=coords('pickup'),b=coords('destination'),driver=state.driver?.location||(state.sessions.driver&&state.lastHeartbeat?coords('driver'):null);
  const points=[a,b,...(driver?[driver]:[])],lat=points.map(p=>p[0]),lon=points.map(p=>p[1]);
  const midLat=(Math.min(...lat)+Math.max(...lat))/2,midLon=(Math.min(...lon)+Math.max(...lon))/2;
  const latSpan=Math.max(.024,Math.max(...lat)-Math.min(...lat))*1.8,lonSpan=Math.max(.035,Math.max(...lon)-Math.min(...lon))*1.7;
  const svg=$('#ride-map'),matrix=svg.getScreenCTM();if(!matrix)return;
  const point=new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix.inverse());
  const target=state.mapTarget;setCoords(target,[midLat-(point.y-275)/550*latSpan,midLon+(point.x-450)/900*lonSpan]);
  $(`#${target}-place`).value=String(places.length-1);state.mapTarget=null;$$('[data-map-target]').forEach(el=>el.classList.remove('active'));
  $('#map-instruction').textContent='Sơ đồ minh họa · Tọa độ mô phỏng';estimate();
});
estimate();render();refreshStatus();refresh();
setInterval(async()=>{if(document.hidden||state.refreshing)return;state.refreshing=true;try{await refresh();}finally{state.refreshing=false;}},2000);
setInterval(()=>{if(!document.hidden)refreshStatus();},10000);
setInterval(async()=>{
  // Only send presence for the visibly active driver account; never re-enable an offline driver.
  if(document.hidden||state.role!=='driver'||!session()||state.busy||state.demo||!state.driver||state.driver.status==='offline'||Date.now()-state.lastHeartbeat<60000)return;
  try{await updateDriver(false,true);}catch{/* User-triggered refresh and status cards expose outages. */}
},15000);
