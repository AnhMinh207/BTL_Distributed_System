/* Leaflet 1.9.4 + real OSM tiles. Browser caching/referrer and visible attribution retained. */
'use strict';
window.GoRideMap={ready:false,map:null,markers:{},latest:null,lastBounds:'',target:null,loadedTiles:0,
  onSelect:null,canSelect:()=>true,
  notice(title,message){
    const panel=document.querySelector('#map-message');panel.hidden=false;
    panel.querySelector('strong').textContent=title;panel.querySelector('p').textContent=message;
  },
  async init(){
    try{
      if(!window.L)throw new Error('Leaflet unavailable');
      const response=await fetch('/api/maps/config',{cache:'no-store'});if(!response.ok)throw new Error('config');
      const config=await response.json();
      this.map=L.map('ride-map',{center:[10.7769,106.7009],zoom:14,scrollWheelZoom:true,zoomControl:false});
      L.control.zoom({position:'bottomright'}).addTo(this.map);
      this.tiles=L.tileLayer(config.tileUrl,{maxZoom:19,updateWhenIdle:true,keepBuffer:0,
        attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'});
      this.tiles.on('tileload',()=>{this.loadedTiles++;document.querySelector('#map-message').hidden=true;});
      this.tiles.on('tileerror',()=>{if(!this.loadedTiles)this.notice('Chưa tải được bản đồ','Kiểm tra kết nối Internet rồi tải lại trang. Bạn vẫn có thể nhập địa chỉ hoặc tọa độ.');});
      this.tiles.addTo(this.map);
      this.map.on('click',event=>{if(event.latlng)this.pick([event.latlng.lat,event.latlng.lng]);});
      this.ready=true;
      document.querySelector('#map-instruction').textContent='OpenStreetMap · Chọn điểm đón hoặc điểm đến rồi bấm trên bản đồ';
      if(this.latest)this.update(this.latest,true);
      this.observer=new ResizeObserver(()=>this.map.invalidateSize({pan:false}));this.observer.observe(document.querySelector('#ride-map'));
      setTimeout(()=>{if(!this.loadedTiles)this.notice('Bản đồ đang mất kết nối','Không tải được dữ liệu đường phố. Kiểm tra mạng rồi tải lại trang; không cần API key.');},12000);
    }catch{this.notice('Không tải được bản đồ','Kiểm tra kết nối và tải lại trang. Bạn vẫn có thể tìm địa chỉ hoặc nhập tọa độ.');}
  },
  update(points,force=false){
    this.latest=points;
    const link=document.querySelector('#open-osm');
    if(points?.pickup)link.href='https://www.openstreetmap.org/?mlat='+points.pickup[0]+'&mlon='+points.pickup[1]+'#map=16/'+points.pickup.join('/');
    if(!this.ready||!points)return;
    const bounds=[];
    for(const [kind,point] of Object.entries(points)){
      if(!point){if(this.markers[kind]){this.markers[kind].remove();delete this.markers[kind];}continue;}
      bounds.push(point);
      if(!this.markers[kind]){
        const labels={pickup:'A',destination:'B',driver:'T'};
        const title={pickup:'Điểm đón',destination:'Điểm đến',driver:'Tài xế'}[kind];
        const icon=L.divIcon({className:'osm-marker '+kind,html:'<span>'+labels[kind]+'</span>',iconSize:[34,42],iconAnchor:[17,42]});
        const marker=L.marker(point,{icon,title,alt:title,draggable:kind!=='driver'}).addTo(this.map);
        marker.on('dragend',()=>{const p=marker.getLatLng();this.pick([p.lat,p.lng],kind);});
        this.markers[kind]=marker;
      }else this.markers[kind].setLatLng(point);
      if(kind!=='driver'){
        const dragging=this.markers[kind].dragging;
        if(this.canSelect())dragging.enable();else dragging.disable();
      }
    }
    const signature=JSON.stringify(points);
    if(bounds.length&&(force||signature!==this.lastBounds)){this.map.fitBounds(bounds,{padding:[55,55],maxZoom:16,animate:false});this.lastBounds=signature;}
  },
  setTarget(kind){
    if(!this.ready||!this.loadedTiles){this.notice('Chưa tải được bản đồ','Chờ dữ liệu bản đồ tải xong hoặc kiểm tra kết nối Internet.');return false;}
    this.target=kind;this.map.getContainer().classList.add('picking-location');return true;
  },
  pick(point,kind=this.target){
    if(!kind)return;
    if(!this.canSelect()){this.update(this.latest,true);return;}
    const wrapped=L.latLng(point).wrap();point=[wrapped.lat,wrapped.lng];
    // Leaflet gives real geographic coordinates directly; no screen-pixel approximation.
    const place={name:kind==='pickup'?'Điểm đón đã chọn':'Điểm đến đã chọn',location:point,
      address:'Vị trí trên OpenStreetMap · '+point.map(n=>n.toFixed(6)).join(', ')};
    this.onSelect?.(kind,place);this.target=null;this.map.getContainer().classList.remove('picking-location');
    document.querySelector('#map-instruction').textContent='Đã chọn vị trí · Có thể kéo ghim A/B để điều chỉnh';
  }
};
