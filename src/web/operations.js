/* Read-only operator dashboard; operations secret stays in memory, not browser storage. */
'use strict';
(()=>{
 let key='';const $=s=>document.querySelector(s);
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const root=$('#operations-panel');
 root.innerHTML='<h2>Giám sát vận hành</h2><p>Queue, retry, circuit breaker, log tập trung và trace. Chỉ người vận hành có quyền xem.</p><form id="operations-login"><label>Mã truy cập vận hành<input id="operations-key" type="password" autocomplete="off" placeholder="OPERATIONS_KEY trong .env" required></label><button class="button primary">Kết nối</button></form><p id="operations-error" role="alert"></p><div id="operations-data" hidden><button class="button secondary small" id="operations-refresh">Làm mới</button><button class="text-button" id="operations-logout">Ngắt kết nối</button><div id="operations-overview"></div><h3>Truy vết chuyến xe</h3><form id="trace-search"><input id="trace-id" placeholder="Correlation ID của chuyến" maxlength="128" pattern="[A-Za-z0-9._-]+" required><button class="button secondary">Xem trace</button></form><div id="trace-list"></div><div id="trace-detail"></div><h3>Log tập trung gần nhất</h3><div id="operations-logs"></div></div>';
 async function get(path){const r=await fetch('/api/operations'+path,{headers:{'X-Operations-Key':key},cache:'no-store',signal:AbortSignal.timeout(5000)});const data=await r.json();if(!r.ok)throw new Error(r.status===403?'Mã truy cập vận hành không đúng.':data.error||'Dịch vụ chưa sẵn sàng.');return data;}
 function table(columns,rows){return '<div class="table-wrap"><table><thead><tr>'+columns.map(c=>'<th>'+esc(c)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+row.map(c=>'<td>'+esc(c)+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';}
 async function refresh(){try{
  const [overview,logs,traces]=await Promise.all([get('/overview'),get('/logs'),get('/traces')]);$('#operations-error').textContent='';$('#operations-data').hidden=false;$('#operations-login').hidden=true;
  const services=Object.values(overview.services);
  $('#operations-overview').innerHTML='<h3>Dịch vụ và outbox</h3>'+table(['Dịch vụ','Instance','Outbox chưa gửi','Inbox đã xử lý','Circuit'],services.map(s=>[s.service,s.instance||'—',s.outbox_pending??'—',s.inbox_processed??'—',(s.circuits||[]).map(c=>c.state+': '+c.endpoint).join('; ')||s.status||'closed']))+
   '<h3>Hàng đợi</h3>'+table(['Queue','Trạng thái','Số lượng'],(overview.queues.queues||[]).map(q=>[q.queue,q.state,q.count]))+
   '<h3>Dead letters</h3>'+table(['Queue','Event ID','Attempts','Lỗi'],(overview.dead_letters.messages||[]).map(m=>[m.queue,m.event_id,m.attempts,m.error]))+
   '<h3>Các instance được phát hiện</h3>'+table(['Dịch vụ','Instance','Trạng thái','Lần thấy cuối'],(overview.instances||[]).map(i=>[i.node,i.instance,i.status,new Date(i.last_seen*1000).toLocaleTimeString('vi-VN')]));
  $('#trace-list').innerHTML=table(['Correlation ID','Dịch vụ','Số bản ghi'],traces.traces.map(t=>[t.trace_id,t.services,t.records]));
  $('#operations-logs').innerHTML=table(['Thời gian','Dịch vụ','Instance','Sự kiện','Kết quả','Correlation ID'],logs.records.map(r=>[r.timestamp,r.node,r.instance,r.event,r.result??'',r.correlation_id]));
 }catch(e){$('#operations-error').textContent=e.message;}}
 $('#operations-login').addEventListener('submit',e=>{e.preventDefault();key=$('#operations-key').value;$('#operations-key').value='';refresh();});
 $('#operations-refresh').addEventListener('click',refresh);
 $('#operations-logout').addEventListener('click',()=>{key='';$('#operations-data').hidden=true;$('#operations-login').hidden=false;$('#trace-detail').innerHTML='';});
 $('#trace-search').addEventListener('submit',async e=>{e.preventDefault();try{const trace=await get('/traces/'+encodeURIComponent($('#trace-id').value));$('#trace-detail').innerHTML=table(['Dịch vụ','Operation / event','Span','Parent span','ms','Kết quả'],trace.records.filter(r=>r.span_id).map(r=>[r.node,r.operation||r.event,r.span_id,r.parent_span_id||'root',r.duration_ms??'',r.result??'']));}catch(e){$('#operations-error').textContent=e.message;}});
 setInterval(()=>{if(key&&!document.hidden&&!$('#view-system').hidden)refresh();},5000);
})();
