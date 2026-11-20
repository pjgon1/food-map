// 앱 화면만 캐시해서 홈 화면 앱처럼 열리게 함 (지도·검색은 항상 인터넷 사용)
const C='food-map-v1'; // 같은 주소의 커피로그 캐시(cafe-map-*)는 건드리지 않음
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(['./','index.html','manifest.json','icon-192.png'])));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k.startsWith('food-map')&&k!==C).map(k=>caches.delete(k)))));self.clients.claim();});
const put=(k,r)=>{if(r.ok){const cp=r.clone();caches.open(C).then(c=>c.put(k,cp));}return r;};
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET')return;
  const u=new URL(e.request.url);
  if(u.origin!==location.origin){
    // 버전이 고정된 로그인 라이브러리·글꼴은 한 번 받으면 폰에 두고 바로 씀
    if(/^cdn\.jsdelivr\.net$/.test(u.host)&&/@\d+\.\d+\.\d+\//.test(u.pathname)||u.host==='fonts.gstatic.com')
      e.respondWith(caches.match(e.request).then(m=>m||fetch(e.request).then(r=>put(e.request,r))));
    return;
  }
  // ?s=, ?v= 같은 주소 꼬리는 빼고 한 칸에만 저장 (캐시가 계속 불어나지 않게)
  const key=e.request.mode==='navigate'?new URL('index.html',self.registration.scope).href:u.origin+u.pathname;
  // 버전 확인용 부분 요청(Range)은 그대로 서버로 (저장 안 함)
  if(e.request.headers.has('range'))return;
  // 앱 화면(index)은 늘 서버에서 새로 받되, 3초 넘게 걸리면(느린 데이터·끊김) 폰에 저장된 것을 먼저 보여줌
  // 서버 응답은 늦게 와도 저장해 둬서 다음에 열 때 새 버전이 뜸
  if(e.request.mode==='navigate'){
    const net=fetch(u.href,{cache:'no-store'}).then(r=>put(key,r));
    e.waitUntil(net.catch(()=>{}));
    e.respondWith(new Promise(res=>{
      let done=false;const go=r=>{if(!done&&r){done=true;res(r);}};
      const t=setTimeout(()=>caches.match(key).then(m=>m&&go(m)),3000);
      net.then(r=>{clearTimeout(t);go(r);}).catch(()=>caches.match(key).then(m=>{clearTimeout(t);if(m)go(m);else{done=true;res(Response.error());}}));
    }));
    return;
  }
  e.respondWith(fetch(e.request).then(r=>put(key,r)).catch(()=>caches.match(key).then(m=>m||caches.match(e.request))));
});
