#!/usr/bin/env python3
"""커피로그(cafe-map) index.html → 맛집로그(food-map) index.html

커피로그를 고친 뒤 이 스크립트를 다시 돌리면 맛집로그도 같은 기능으로 다시 만들어짐.
바꿀 곳을 못 찾으면(커피로그 코드가 바뀐 경우) 멈추고 어디인지 알려줌.

사용: python3 make_food.py <cafe-map/index.html> <food-map 폴더>
"""
import base64, hashlib, re, sys, pathlib

SRC, OUT = sys.argv[1], pathlib.Path(sys.argv[2])
HERE = pathlib.Path(__file__).parent
s = open(SRC, encoding='utf-8').read()


def rep(old, new, n=1):
    """old 가 정확히 n번 있어야 바꿈 (n=0 이면 1번 이상 전부)"""
    global s
    c = s.count(old)
    if (n and c != n) or (not n and c == 0):
        sys.exit(f'바꿀 곳 개수가 달라요 ({c}개, 기대 {n or "1+"}): {old[:80]!r}')
    s = s.replace(old, new)


def rep_block(start, end, new):
    """start 로 시작해서 end 로 끝나는 덩어리 하나를 통째로 바꿈"""
    global s
    i = s.find(start)
    if i < 0 or s.count(start) != 1:
        sys.exit(f'덩어리 시작을 못 찾았어요: {start[:60]!r}')
    j = s.find(end, i)
    if j < 0:
        sys.exit(f'덩어리 끝을 못 찾았어요: {end[:60]!r}')
    s = s[:i] + new + s[j + len(end):]


VERSION = '2026.11.21-15'

# ---------------------------------------------------------------
# 1) 같은 주소(pjgon1.github.io)를 쓰는 커피로그와 이 기기 저장 칸이 안 섞이게
# ---------------------------------------------------------------
rep('Object.keys(localStorage)', 'LS.keys()')
rep('localStorage.', 'LS.', 0)
rep('sessionStorage.', 'SS.', 0)
if 'localStorage' in s or 'sessionStorage' in s:
    sys.exit('저장 칸 이름 바꾸기가 덜 됐어요')
SHIM = """<script>
/* 맛집로그는 커피로그와 같은 주소(pjgon1.github.io)를 써서, 이 기기 저장 칸 이름 앞에 'food:'를 붙여 따로 씀 */
const nsStore = (get, P = 'food:') => ({
  getItem: k => get().getItem(P + k), setItem: (k, v) => get().setItem(P + k, v), removeItem: k => get().removeItem(P + k),
  keys: () => Object.keys(get()).filter(k => k.startsWith(P)).map(k => k.slice(P.length)),
});
const LS = nsStore(() => window.localStorage), SS = nsStore(() => window.sessionStorage);
/* ========================================================="""
rep('<script>\n/* =========================================================\n   설정값', SHIM + '\n   설정값')

# 기기 안 기록 저장소 (IndexedDB) 이름
rep("('cafe-map-sv')", "('food-map-sv')")
rep("openDb('cafe-map', ", "openDb('food-map', ", 2)
rep("openDb('cafe-map-sv', ", "openDb('food-map-sv', ")
# 백업 파일 표시
rep("app: 'cafe-map'", "app: 'food-map'")
rep("data.app !== 'cafe-map'", "data.app !== 'food-map'")
# 앱 화면 캐시: 내 것만 지움
rep("for (const k of await caches.keys()) await caches.delete(k);",
    "for (const k of await caches.keys()) if (k.startsWith('food-map')) await caches.delete(k);")
if 'cafe-map' in s:
    sys.exit('cafe-map 이름이 남아 있어요')

# ---------------------------------------------------------------
# 2) 서버: 로그인·친구·아이디는 커피로그와 같이, 기록·사진·공유·설정은 따로
# ---------------------------------------------------------------
rep("const SB_KEY = ", "const SBT = { cafes: 'food_places', visits: 'food_visits' }; // 맛집로그 기록 표 (커피로그는 cafes/visits)\nconst SB_KEY = ")
rep("let q = client.from(store).select(", "let q = client.from(SBT[store]).select(")
rep("rpc('sync_push'", "rpc('food_sync_push'")
rep("rpc('friend_records'", "rpc('food_friend_records'")
rep("rpc('get_share'", "rpc('food_get_share'")
rep("from('shares')", "from('food_shares')", 3)
rep("from('user_prefs')", "from('food_user_prefs')", 7)
rep("storage.from('photos')", "storage.from('food-photos')", 5)
# 로그인 세션도 커피로그와 따로 보관 (한쪽에서 로그아웃해도 다른 쪽은 그대로)
rep("{ auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, flowType: 'pkce' } }",
    "{ auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, flowType: 'pkce', storage: LS, storageKey: 'sb-food-auth-token' } }")
rep("const { error } = await sb.auth.signOut(); serverOut = !error;",
    "const { error } = await sb.auth.signOut({ scope: 'local' }); serverOut = !error;")
for bad in ["from('cafes')", "from('visits')", "rpc('sync_push'", "from('photos')", "from('shares')", "from('user_prefs')"]:
    if bad in s:
        sys.exit('커피로그 서버 이름이 남아 있어요: ' + bad)

# ---------------------------------------------------------------
# 3) 카카오 장소 검색: 음식점 먼저
# ---------------------------------------------------------------
rep("places.categorySearch('CE7', (d, st) => r(", "places.categorySearch('FD6', (d, st) => r(")
rep("for (const code of ['CE7', 'FD6'])", "for (const code of ['FD6', 'CE7'])")
rep("for (const cat of ['CE7', 'FD6']) places.categorySearch(cat, (r, st) => { if (st === kakao.maps.services.Status.OK) got.push(...(cat === 'FD6' ? r.filter(x => /카페|디저트|제과|베이커리|간식|도넛|아이스크림|떡|빙수|차,/.test(x.category_name)) : r)); done(); }",
    "for (const cat of ['FD6', 'CE7']) places.categorySearch(cat, (r, st) => { if (st === kakao.maps.services.Status.OK) got.push(...r); done(); }")
rep("const isCafe = /카페|커피|디저트|베이커리|제과/.test(p.category_name);",
    "const isCafe = p.category_group_code === 'FD6' || /음식점/.test(p.category_name || '');")
rep("const rank = p => p.category_group_code === 'CE7' || /카페|커피|디저트|베이커리|제과/.test(p.category_name) ? 0 : p.category_group_code === 'FD6' ? 1 : 2;",
    "const rank = p => p.category_group_code === 'FD6' || /음식점/.test(p.category_name || '') ? 0 : p.category_group_code === 'CE7' ? 1 : 2;")

# ---------------------------------------------------------------
# 4) 식당용 내용: 태그, 항목 별점, 메뉴 종류, 뱃지, 그림
# ---------------------------------------------------------------
rep_block("const TAGS = [", "];",
          "const TAGS = ['혼밥 가능','빠르게 먹기 좋음','가성비','양 많음','무한리필·뷔페','데이트','특별한 날','모임·회식','룸 있음','분위기 좋음','뷰 좋음','야외 좌석','조용함','친절함','술 한잔',"
          "'포장 가능','예약 추천','웨이팅 있음','주차 가능','브레이크타임 없음','아침식사 가능','심야 영업','배달 가능','테이크아웃 전문'];\n"
          "const TAGS_OPS = ['포장 가능','예약 추천','웨이팅 있음','주차 가능']; // 이용 칸\n"
          "const HOURS = ['브레이크타임 없음','아침식사 가능','심야 영업','배달 가능','테이크아웃 전문']; // 영업 정보: 상세 화면 주소 밑에 작은 글씨로 (태그로 저장해서 거르기는 그대로)")
rep("const SUBS = [['taste', '맛'], ['mood', '분위기'], ['seat', '자리'], ['pref', '취향']];",
    "const SUBS = [['taste', '맛'], ['value', '가성비'], ['mood', '분위기'], ['pref', '취향']];")
MENU = r"""const MENU_GROUPS = [
  ['국밥·탕', /국밥|해장국|설렁탕|곰탕|갈비탕|감자탕|순대국|순댓국|내장탕|도가니탕|삼계탕|추어탕|매운탕|육개장|소머리|선지|뼈해장|수육국밥|탕$/],
  ['죽·수프', /죽$|수프|스프|차우더|포타주/],
  ['찌개·전골', /찌개|전골|부대|짜글이|순두부|청국장|샤브/],
  ['찜·조림', /찜$|찜닭|아구찜|아귀찜|갈비찜|해물찜|조림|코다리/],
  ['카레', /카레|커리|^난$|탄두리/],
  ['아시안', /쌀국수|팟타이|분짜|반미|나시고랭|나시고렝|미고랭|미고렝|똠얌|똠양|팟카파오|카오팟|월남쌈|락사|바쿠테/],
  ['만두·딤섬', /만두|딤섬|샤오롱|교자|바오|쇼마이|하가우/],
  ['면·국수', /칼국수|국수|냉면|막국수|밀면|비빔면|쫄면|수제비|우동|소바|라멘|라면|파스타면/],
  ['중식', /짜장|짬뽕|탕수육|마라|훠궈|양장피|깐풍|유린기|볶음밥|고추잡채|꿔바로우|멘보샤|팔보채|양꼬치|동파육/],
  ['족발·보쌈', /족발|보쌈|수육|편육/],
  ['초밥·회', /초밥|스시|사시미|오마카세|^회$|모둠회|물회|회덮밥|숙성회|활어|연어|참치/],
  ['해산물', /해물|조개|대게|킹크랩|게장|낙지|쭈꾸미|주꾸미|오징어|문어|새우|전복|생선|갈치|고등어|꽃게|홍합|장어|굴$/],
  ['곱창·막창', /곱창|막창|대창|소창|양곱창|곱도리/],
  ['고기구이', /삼겹|오겹|목살|항정|가브리|갈매기|돼지갈비|소갈비|^갈비$|양념갈비|생갈비|등심|안심|차돌|우삼겹|살치|채끝|토시|갈비살|한우|숯불|불고기|닭갈비|오리|바비큐|바베큐|폭립|등갈비|양갈비|양고기|야키니쿠|떡갈비|구이$/],
  ['치킨', /치킨|닭강정|후라이드|프라이드|순살|닭다리|윙/],
  ['덮밥', /덮밥|돈부리|규동|사케동|가츠동|카츠동|오야코동|에비동|부타동|우나동|텐동|우나기|히츠마부시/],
  ['돈까스·튀김', /돈까스|돈가스|카츠|커틀릿|가라아게|튀김|덴뿌라/],
  ['일식', /규카츠|오코노미|타코야키|야키토리|스키야키|나베|오차즈케|야키소바/],
  ['분식', /떡볶이|김밥|순대|어묵|오뎅|라볶이|쫄볶|주먹밥|컵밥|토스트|떡꼬치|소떡|호떡|붕어빵|계란빵/],
  ['피자', /피자/],
  ['빵·베이커리', /빵$|식빵|크루아상|크로와상|베이글|바게트|스콘|휘낭시에|마들렌|타르트|브레드|깜빠뉴|치아바타|소보로|베이커리/],
  ['버거·샌드위치', /버거|샌드위치|샌드$|핫도그|타코|부리또|브리또/],
  ['파스타·양식', /파스타|스파게티|알리오|까르보|봉골레|라자냐|뇨끼|뇨키|리조또|스테이크|함박|그라탕|필라프|감바스/],
  ['샐러드·브런치', /샐러드|포케|브런치|오믈렛|팬케이크|프렌치\s*토스트|와플|크로플|아사이/],
  ['밥·백반', /비빔밥|백반|정식|한정식|쌈밥|오므라이스|제육|불백|도시락|솥밥|돌솥|정찬|밥$/],
  ['전·부침', /전$|파전|부침|빈대떡|육전|동그랑땡/],
  ['술', /소주|맥주|생맥|하이볼|와인|막걸리|사케|칵테일|위스키|고량주|전통주/],
  ['떡·전통간식', /인절미|약과|한과|유과|송편|백설기|시루떡|꿀떡|찹쌀떡|가래떡|쑥떡|경단|양갱|식혜|수정과|떡케이크|떡$/],
  ['아이스크림·빙수', /아이스크림|빙수|젤라또|소프트콘|셔벗|소르베|파르페|아포가토/],
  ['디저트·음료', /케이크|커피|라떼|아메리카노|에이드|주스|콜라|사이다|음료|마카롱|쿠키|도넛|푸딩|크레페|차$/],
];"""
rep_block("const MENU_GROUPS = [", "];\n", MENU + "\n")
rep('placeholder="아인슈페너, 크로플, 소금빵…"', 'placeholder="김치찌개, 돈까스, 냉면…"')
rep('placeholder="아인슈페너, 바스크치즈케이크"', 'placeholder="김치찌개, 계란말이"')
rep('placeholder="바스크치즈케이크, 시즌 라떼…"', 'placeholder="수육, 계절 메뉴…"')
rep('placeholder="맛, 분위기, 자리, 웨이팅… 생각나는 대로"', 'placeholder="맛, 양, 웨이팅, 분위기… 생각나는 대로"')
rep('메모 (와이파이 비번, 주차 팁 같은 거)', '메모 (주차 팁, 추천 자리 같은 거)')
# 방문 기록: 몇 명이서 → 1인 가격
rep("""placeholder="13,500">""", """placeholder="13,500">
    <div class="tagpick" id="vPpl" style="margin-top:8px;align-items:center"><span class="small" style="margin-right:2px">몇 명이서?</span>${[1,2,3,4,5,6].map(n => `<button type="button" class="chip ${(+v.people||0)===n?'on':''}" data-n="${n}" style="font-size:12px;padding:5px 10px">${n===6?'6명+':n+'명'}</button>`).join('')}</div>
    <div class="small" id="vPer" style="margin:6px 2px 0"></div>""")
rep("  $('#vPrice').oninput = e => { const n = e.target.value.replace(/[^\\d]/g,''); e.target.value = n ? Number(n).toLocaleString('ko-KR') : ''; };",
    """  const perShow = () => { const pr = +$('#vPrice').value.replace(/[^\\d]/g,''), b = document.querySelector('#vPpl .chip.on'), n = b ? +b.dataset.n : 0; $('#vPer').textContent = pr && n > 1 ? `1인 ${won(Math.round(pr / n / 100) * 100)}` : pr && !n ? '인원을 고르면 1인 가격이 나와요' : ''; };
  $('#vPrice').oninput = e => { const n = e.target.value.replace(/[^\\d]/g,''); e.target.value = n ? Number(n).toLocaleString('ko-KR') : ''; perShow(); };
  $('#vPpl').onclick = e => { const b = e.target.closest('.chip'); if (!b) return; const on = !b.classList.contains('on'); document.querySelectorAll('#vPpl .chip').forEach(x => x.classList.remove('on')); b.classList.toggle('on', on); perShow(); };
  perShow();""")
rep("  v.price = $('#vPrice').value.replace(/[^\\d]/g,'');",
    "  v.price = $('#vPrice').value.replace(/[^\\d]/g,'');\n  { const b = document.querySelector('#vPpl .chip.on'); if (b) v.people = +b.dataset.n; else delete v.people; }")
rep("${esc(v.menu)}${v.menu&&v.price?' · ':''}${won(v.price)}", "${esc(v.menu)}${v.menu&&v.price?' · ':''}${won(v.price)}${v.price && +v.people > 1 ? ` (${v.people >= 6 ? '6명+' : v.people + '명'} · 1인 ${won(Math.round(v.price / v.people / 100) * 100)})` : ''}")
# 오늘 어디 갈까: 1인 얼마까지
rep("    <div class=\"tagpick\">${chips([[0,'상관없음'],[0.5,'500m'],[1,'1km'],[3,'3km'],[10,'10km']], pickOpt.dist, 'ds')}</div>",
    "    <div class=\"tagpick\">${chips([[0,'상관없음'],[0.5,'500m'],[1,'1km'],[3,'3km'],[10,'10km']], pickOpt.dist, 'ds')}</div>\n    <label class=\"f\">1인 얼마까지? <span class=\"small\" style=\"font-weight:400\">(인원 적은 기록이 있는 곳만)</span></label>\n    <div class=\"tagpick\">${chips([[0,'상관없음'],[10000,'1만원'],[20000,'2만원'],[30000,'3만원']], pickOpt.price || 0, 'pr')}</div>")
rep("    if (ds) { pickOpt.dist = +ds.dataset.ds;", "    { const pr = e.target.closest('[data-pr]'); if (pr) { pickOpt.price = +pr.dataset.pr; pr.parentElement.querySelectorAll('.chip').forEach(x => x.classList.toggle('on', x === pr)); } }\n    if (ds) { pickOpt.dist = +ds.dataset.ds;")
rep("    if (pickOpt.dist && distKm(myPos, c) > pickOpt.dist) return false;", "    if (pickOpt.dist && distKm(myPos, c) > pickOpt.dist) return false;\n    if (pickOpt.price && !(perPerson(c) && perPerson(c) <= pickOpt.price)) return false;")
rep("        if (pickOpt.dist && distKm(myPos, c) > pickOpt.dist) continue;", "        if (pickOpt.dist && distKm(myPos, c) > pickOpt.dist) continue;\n        if (pickOpt.price) continue; // 친구 식당은 1인 가격을 몰라서 뺌")
rep("prompt('새 종류 이름 (예: 시즌 음료)')", "prompt('새 종류 이름 (예: 계절 메뉴)')")
rep('placeholder="예: 재곤, jaegon_cafe"', 'placeholder="예: 재곤, jaegon_food"')
rep('예: 모모커피 성수, 동성로 카페', '예: 동성로 돈까스, 수성못 파스타')

# 뱃지 (식당용 이름, 플렉스는 5만 원)
rep("['rv20', '카페 평론가', '후기 20개 쓰기', 'reviews', 20]", "['rv20', '미식 평론가', '후기 20개 쓰기', 'reviews', 20]")
rep("['mo5', '카페 중독', '한 달에 5번 방문', 'month', 5]", "['mo5', '외식 중독', '한 달에 5번 방문', 'month', 5]")
rep("['f1', '인생 카페', '별점 5점 주기', 'five', 1]", "['f1', '인생 맛집', '별점 5점 주기', 'five', 1]")
rep("['we5', '주말엔 카페', '토·일요일에 5번 방문', 'weekend', 5]", "['we5', '주말엔 외식', '토·일요일에 5번 방문', 'weekend', 5]")
rep("['st3', '사흘 연속 출근', '3일 연속 카페 가기', 'streak', 3]", "['st3', '사흘 연속 외식', '3일 연속 맛집 가기', 'streak', 3]")
rep("['fx', '오늘은 플렉스', '한 번에 3만 원 이상', 'flex', 1]", "['fx', '오늘은 플렉스', '한 번에 5만 원 이상', 'flex', 1]")
rep("flex: vd.filter(v => +v.price >= 30000).length", "flex: vd.filter(v => +v.price >= 50000).length")

# 그림: 컵 → 음식
arts = open(HERE / 'arts.txt', encoding='utf-8').read().strip()
i = s.find('const CUP_ARTS = (() => {')
j = s.find('  return [\n', i)
k = s.find('];\n})();', j)
if min(i, j, k) < 0:
    sys.exit('컵 그림 덩어리를 못 찾았어요')
s = s[:j] + '  return [\n' + arts.rstrip(',') + s[k:]
# 핀 그림: 음식(이름·분류) → 그 음식과 같이 파는 메뉴 그림들, 아니면 종류별 그림들 중에서 날마다 돌아가며 (좌우 뒤집기도). 종류 없음은 전체에서
KIND_ARTS = "const KIND_ARTS = {'한식': [0, 2, 13, 31, 32, 33, 34, 35, 36, 37, 38, 39, 42, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 88, 90, 92, 93, 94, 95, 96, 97, 40, 41, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133], '양식': [56, 62, 63, 64, 27, 134, 135, 136, 137, 138, 139, 140, 141, 142], '일식': [3, 1, 15, 30, 43, 44, 45, 40, 103, 104, 105, 106, 11, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153], '중식': [8, 18, 19, 20, 46, 47, 48, 107, 108, 109, 154, 155, 156, 157, 158], '아시안': [21, 22, 23, 49, 48, 110, 111, 112, 159, 160, 161, 162, 163, 164, 165], '분식': [9, 10, 29, 50, 51, 98, 99, 100, 101, 166, 167, 168, 169, 170], '패스트푸드': [4, 61, 5, 53, 6, 52, 16, 101, 102, 141, 143, 170], '술집': [24, 25, 26, 7, 54, 55, 83, 89, 76, 147, 153, 139, 140], '기타': [58, 59, 60, 57, 14, 28, 17, 11, 12, 113, 114, 115, 171, 172, 173, 174, 175, 176, 177, 178]};"
ART_KEYS = r"""// 이름·카카오 분류로 음식이 보이면 그 음식 그림들 중에서 (위에서부터 먼저 맞는 것), 아니면 종류별 그림 중에서
const ART_KEYS = [
  [/도시락|한솥/, [17, 32]], [/라볶이/, [98, 9]], [/떡꼬치/, [166, 9]], [/소떡/, [167, 166]], [/떡볶이|떡볶기/, [9, 98, 100, 10, 166]], [/김밥/, [10, 9, 50]],
  [/순댓국|순대국/, [71, 33]], [/순대/, [99, 9, 71]], [/어묵|오뎅/, [29, 9]], [/붕어빵|잉어빵/, [168]], [/호떡/, [169]], [/닭강정/, [170, 52]],
  [/분식/, [9, 10, 29, 98, 100, 50, 166, 167]], [/주먹밥|오니기리/, [30]], [/토스트/, [101]], [/샌드위치|서브웨이/, [102, 101]],
  [/수제버거/, [141, 4, 61]], [/핫도그|콘도그/, [51]], [/버거/, [4, 61, 141, 16]], [/고르곤졸라/, [64, 53]], [/피자/, [5, 53, 64]], [/피시앤칩스|피쉬앤칩스/, [143]], [/감자튀김|프렌치프라이/, [16, 4]],
  [/월남쌈/, [111, 21]], [/반미/, [23, 21]], [/분짜/, [163, 21, 111]], [/쌀국수|베트남/, [21, 111, 23, 163]], [/똠얌|똠양/, [159, 49]], [/뿌팟퐁|푸팟퐁/, [160]],
  [/태국|팟타이/, [49, 21, 159, 160]], [/나시고렝|나시고랭/, [161, 162]], [/미고렝|미고랭/, [162, 161]], [/인도네시아|발리/, [161, 162]], [/락사|싱가포르|말레이/, [164, 165]], [/바쿠테|바쿠테/, [165]],
  [/인도|(^|[^이])커리/, [110, 22]], [/카레/, [22, 110]],
  [/포케|하와이/, [112, 28]], [/타코야끼|타코야키/, [105]], [/타코|멕시/, [113, 114]], [/부리토|브리또/, [114, 113]], [/케밥|터키/, [115]],
  [/마라샹궈/, [107, 47]], [/훠궈/, [108, 47]], [/마라/, [47, 107]], [/양꼬치/, [109, 7]], [/유린기/, [154, 19]], [/깐풍/, [155, 154]], [/고추잡채|꽃빵/, [156]], [/동파육/, [157]], [/양장피/, [158]],
  [/탕수육|꿔바로우/, [19, 18]], [/딤섬|샤오롱/, [20, 8]],
  [/짜장|짬뽕|반점|중화|중국집|중식/, [18, 46, 19, 48, 155, 158]], [/만두|교자/, [8, 20]], [/볶음밥/, [48, 18]],
  [/텐동/, [103, 15]], [/초밥|스시|오마카세|사시미/, [3, 40]], [/물회/, [84, 40]], [/횟집|회타운|회센터|활어|(^|\s)회($|\s)/, [40, 84, 3, 41, 129]],
  [/장어덮밥|우나기|히츠마부시/, [150, 85]], [/장어/, [85, 150]], [/해물찜/, [127, 86]], [/아귀|아구/, [86, 127]], [/낙지|쭈꾸미|주꾸미/, [87, 88]], [/오징어/, [88, 87]],
  [/조개찜/, [131, 89]], [/조개/, [89, 131, 91]], [/게장/, [126]], [/대게|킹크랩|크랩/, [90]], [/새우/, [91, 89]], [/알탕/, [128]], [/매운탕/, [129, 128]],
  [/고등어|삼치|꽁치/, [130, 41]], [/생선|갈치|임연수/, [41, 130, 40]], [/전복/, [132]], [/(^|\s)죽($|\s)|죽집|본죽/, [132]], [/굴국|(^|\s)굴($|\s)|굴보쌈/, [133]],
  [/라멘/, [1, 43]], [/우동/, [43, 1]], [/냉소바|자루소바/, [151, 104]], [/야키소바/, [148]], [/소바|메밀/, [104, 151, 95]], [/오코노미야끼|오코노미야키/, [106, 105]],
  [/가츠동/, [144, 44]], [/규동/, [145, 45]], [/돈까스|돈가스|카츠/, [44, 15, 144]], [/가라아게/, [146, 15]], [/튀김/, [100, 15]],
  [/덮밥|돈부리|사케동|부타동|오야꼬동/, [45, 103, 144, 145, 150]], [/오차즈케/, [149]], [/오므라이스|경양식|함박/, [11, 44]], [/라면/, [50, 98]],
  [/모츠나베/, [153]], [/나베|스키야키/, [152, 153]], [/야키토리|꼬치구이|쿠시/, [147, 7]],
  [/하이볼|칵테일|위스키/, [26, 54]], [/와인/, [54, 64, 26, 139]], [/막걸리|전집|파전|빈대떡|부침/, [55, 42]], [/호프|맥주|비어|브루|펍/, [24, 6, 52, 16, 143]],
  [/소주|포차|포장마차/, [25, 7, 83, 88]], [/닭발/, [83, 25]], [/이자카야|일본식주점|선술집/, [147, 7, 26, 153, 146, 105]], [/꼬치|주점/, [7, 26, 24, 54, 147]],
  [/리조또|리소토/, [63, 62]], [/까르보나라/, [134, 62]], [/봉골레/, [135]], [/알리오/, [136]], [/라자냐/, [138]], [/뇨끼|뇨키/, [137]], [/감바스/, [139]],
  [/바비큐|바베큐|립/, [140, 27]], [/스테이크|그릴/, [27, 75, 140]], [/수프|스프/, [142]],
  [/파스타|스파게티|이탈리안|이탈리아/, [56, 62, 63, 64, 134, 135, 136, 137, 138]],
  [/샐러드|비건/, [28, 112]], [/아사이/, [178, 28]], [/브런치|에그|팬케이크/, [57, 14, 28, 171]], [/크로플/, [172, 171]], [/와플/, [171, 172]], [/도넛|도너츠/, [173]], [/푸딩/, [174]],
  [/마카롱/, [175]], [/크레페|크레프/, [176]], [/베이글/, [177]], [/베이커리|제과|빵/, [177, 173, 58, 172]],
  [/케이크|디저트|빙수|아이스크림|젤라또/, [58, 59, 60, 171, 174, 175, 176]],
  [/샤브/, [97]], [/삼계탕|백숙/, [34]], [/닭한마리/, [122, 34]], [/부대/, [35]], [/감자탕|뼈해장/, [68, 33]], [/갈비탕/, [69, 70]], [/곰탕/, [121, 70]], [/설렁탕/, [70, 121]], [/육개장/, [67, 2]],
  [/추어탕|추어/, [120]], [/청국장/, [119, 65]], [/김치찌개/, [118, 2]],
  [/해장국|국밥/, [33, 71, 70, 2]], [/미역국/, [72]], [/순두부/, [66, 2, 65]], [/된장/, [65, 2, 119]], [/찌개|전골/, [2, 65, 66, 35, 118]],
  [/닭볶음탕|닭도리탕/, [74, 78]], [/찜닭/, [117, 74]], [/닭갈비/, [78, 74]], [/갈비찜/, [116, 37]],
  [/냉면|밀면/, [38, 95]], [/막국수/, [95, 38]], [/콩국수/, [94, 92]], [/칼국수/, [39, 92, 96]], [/잔치국수|국수/, [92, 39]], [/수제비/, [96, 39]], [/쫄면/, [93, 9]],
  [/해물/, [73, 86, 127]], [/찜($|\s)/, [86, 74, 116, 117]], [/탕($|\s)/, [33, 2, 68]],
  [/치킨|통닭|후라이드|닭요리/, [6, 52, 24, 170]],
  [/족발/, [80, 81]], [/보쌈/, [81, 80]], [/육회비빔밥/, [124, 82]], [/꼬막/, [125]], [/육회|육사시미/, [82, 75, 124]], [/쌈밥|쌈/, [36, 32]], [/제육/, [79, 32]], [/불고기/, [77, 79]],
  [/곱창|막창|대창/, [76, 75]], [/오리/, [123, 13]], [/갈비/, [37, 13, 77, 116]], [/소고기|한우|등심|안심|차돌|살치|우대/, [75, 27, 37]], [/고기|구이|삼겹|숯불|목살|항정|정육/, [13, 75, 37, 36, 123]],
  [/비빔밥|돌솥/, [31, 0, 124, 125]], [/백반|한정식|정식|밥상|솥밥|가정식|기사식당/, [32, 31, 0]],
];
const artPool = c => {
  if (!c) return null;
  const find = s => { for (const [re, a] of ART_KEYS) if (re.test(s)) return a; return null; };
  return find(c.name || '') || find(menusOf(c)) || find((c.category || '').split(' > ').slice(1).join(' ')); // 이름 → 기록한 메뉴 → 카카오 분류
};"""
rep("})();\nconst coverOf = ", "})();\n" + KIND_ARTS + "\n" + ART_KEYS + "\nconst coverOf = ")
rep("function cupIcon(id){", "function cupIcon(id, c){")
rep("  return `<svg class=\"cup\" viewBox=\"0 0 32 32\" aria-hidden=\"true\">${CUP_ARTS[(h >>> 0) % CUP_ARTS.length]}</svg>`;",
    "  const cc = c || cafes.find(x => x.id === id), pool = artPool(cc) || [...new Set(kindsOf(cc).flatMap(k => KIND_ARTS[k] || []))];\n  const art = pool.length ? CUP_ARTS[pool[(h >>> 0) % pool.length]] : CUP_ARTS[(h >>> 0) % CUP_ARTS.length];\n  return `<svg class=\"cup\" viewBox=\"0 0 32 32\" aria-hidden=\"true\">${(h >>> 9) & 1 ? `<g transform=\"matrix(-1 0 0 1 32 0)\">${art}</g>` : art}</svg>`;")
rep("cupIcon(c.id)", "cupIcon(c.id, c)", 0)
rep("cupIcon(g.c.id)", "cupIcon(g.c.id, g.c)")
rep_block("  cup: '<svg class=\"ic2\" viewBox=\"0 0 24 24\" aria-hidden=\"true\">", "</svg>',\n",
          "  cup: '<svg class=\"ic2\" viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"M9 5.6c-.6-.8.6-1.4 0-2.3M12.2 5c-.6-.8.6-1.4 0-2.3M15.4 5.6c-.6-.8.6-1.4 0-2.3\" fill=\"none\" stroke=\"#C9B8AC\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M5 11c0-2.9 3.2-4.5 7.2-4.5s7.2 1.6 7.2 4.5z\" fill=\"#fff\" stroke=\"#5B4636\" stroke-width=\"1.1\" stroke-linejoin=\"round\"/><path d=\"M3.6 11h17.2a8.6 8.6 0 0 1-17.2 0z\" fill=\"#FFE3EA\" stroke=\"#5B4636\" stroke-width=\"1.3\" stroke-linejoin=\"round\"/><circle cx=\"9.4\" cy=\"14.6\" r=\".6\" fill=\"#5B4636\"/><circle cx=\"15\" cy=\"14.6\" r=\".6\" fill=\"#5B4636\"/><path d=\"M11.6 15.9q.6.5 1.2 0\" fill=\"none\" stroke=\"#5B4636\" stroke-width=\".8\" stroke-linecap=\"round\"/><circle cx=\"8\" cy=\"15.8\" r=\".8\" fill=\"#FFB3C1\"/><circle cx=\"16.4\" cy=\"15.8\" r=\".8\" fill=\"#FFB3C1\"/></svg>',\n")

# 색 테마: 맛집로그 기본은 '고추장'
rep("const THEMES = [\n", "const THEMES = [\n  {k:'gochujang',n:'고추장',    bg:'#FFF9F5',ink:'#3A221C',sub:'#9C7D73',acc:'#C9472D',onacc:'#fff',soft:'#FCE2D9',softt:'#A63A22',note:'#FDF0EA',heart:'#FCE7EA',heartt:'#C2405E',line:'#F4DDD3',frame:'#fff',ph:'#F6CFC1'},\n")
THEME_NAMES = {  # 색은 그대로, 이름만 음식으로
    '커피 베이지': '누룽지', '말차 라떼': '깻잎', '바닐라 크림': '계란말이', '딸기 우유': '명란', '얼그레이': '메밀',
    '소다 라떼': '물냉면', '자몽 에이드': '떡볶이', '블루베리 요거트': '가지', '흑임자': '짜장', '밤 카페 (다크)': '심야 식당 (다크)',
    '호지차 라떼': '된장', '레몬 마들렌': '단무지', '민트 초코': '미나리', '복숭아 아이스티': '연어', '라벤더 라떼': '자색고구마',
    '카라멜 마키아또': '돈까스', '유자차': '카레', '체리 콕': '김치', '바다 소금빵': '물회', '심야 라운지 (다크)': '포장마차 (다크)',
}
for a, b in THEME_NAMES.items():
    rep(f"n:'{a}'", f"n:'{b}'")
rep("let cur = 'coffee'; try { cur = LS.getItem('theme') || 'coffee'; }", "let cur = 'gochujang'; try { cur = LS.getItem('theme') || 'gochujang'; }")
rep("let th = 'coffee'; try { th = LS.getItem('theme') || 'coffee'; }", "let th = 'gochujang'; try { th = LS.getItem('theme') || 'gochujang'; }")
rep('<meta name="theme-color" content="#FFFDF9">', '<meta name="theme-color" content="#FFF9F5">')

# ---------------------------------------------------------------
# 4b) 종류 (한식·양식·일식…): 직접 고른 값이 없으면 카카오 분류로 자동
# ---------------------------------------------------------------
KIND_JS = r"""const KINDS = ['한식', '양식', '일식', '중식', '아시안', '분식', '패스트푸드', '술집', '기타'];
// 종류: 식당 정보에서 고른 값 → 없으면 카카오 분류(음식점 > 한식 > …)로 자동
const autoKind = cat => {
  const s = cat || ''; if (!s) return '';
  if (/술집|주점|호프|이자카야|포장마차|와인바|칵테일바|맥주/.test(s)) return '술집';
  if (/패스트푸드|햄버거|치킨|핫도그/.test(s)) return '패스트푸드';
  if (/분식|떡볶이|김밥|호떡|붕어빵|떡꼬치/.test(s)) return '분식';
  if (/일식|일본식|초밥|스시|돈까스|돈가스|라멘|우동/.test(s)) return '일식';
  if (/중식|중국요리|양꼬치|마라/.test(s)) return '중식';
  if (/아시아|베트남|태국|인도|동남아|쌀국수|멕시|터키|중동/.test(s)) return '아시안';
  if (/양식|이탈리|프랑스|스페인|스테이크|파스타|패밀리레스토랑/.test(s)) return '양식';
  if (/피자|샌드위치|토스트/.test(s)) return '패스트푸드';
  if (/한식|국밥|해장국|고기|해물|생선|찌개|냉면|삼계탕|족발|보쌈|백반|칼국수|국수/.test(s)) return '한식';
  return '기타';
};
// 여러 개 고를 수 있음 (예전 기록은 글자 하나로 저장돼 있음)
const kindsOf = c => { if (!c) return []; const k = c.kind; if (Array.isArray(k)) return k; if (k) return [k]; const a = autoKind(c.category); return a ? [a] : []; };
const kindOf = c => kindsOf(c)[0] || '';
// 내 방문 기록에 적은 메뉴들 (친구 식당은 없음)
const menusOf = c => (c && c.id && typeof visits !== 'undefined') ? visits.filter(v => v.cafeId === c.id && v.menu).map(v => v.menu).join(' ') : '';
// 1인 가격: 인원을 적은 방문들의 (쓴 돈 ÷ 인원) 평균, 백 원 단위
const perPerson = c => { if (!c || !c.id || typeof visits === 'undefined') return 0; const a = visits.filter(v => v.cafeId === c.id && +v.price > 0 && +v.people > 0).map(v => v.price / v.people); return a.length ? Math.round(a.reduce((x, y) => x + y, 0) / a.length / 100) * 100 : 0; };
// 음식 성격: 종류와 따로 겹쳐서 붙음 (막국수 = 한식 + 면, 라볶이 = 분식 + 면 + 매운거)
// 식당 정보에서 고른 값 → 없으면 이름·카카오 분류로 자동
const FEATS = ['고기', '해산물', '채소', '면', '밥', '빵', '국물', '구이', '찜', '튀김', '날것', '매운거', '안주', '디저트'];
const FEAT_KEYS = {
  '고기': /고기|육류|삼겹|목살|항정|갈비|불고기|한우|등심|차돌|곱창|막창|대창|족발|보쌈|제육|스테이크|바베큐|숯불|정육|오리|양꼬치|닭갈비|육회|바비큐|바베큐|립|동파육|수육|닭한마리|찜닭|야키토리/,
  '해산물': /해물|해산물|횟집|회센터|회타운|회식당|(^|\s)회($|\s)|활어|물회|사시미|초밥|스시|오마카세|수산|생선|조개|대게|킹크랩|꽃게|게장|크랩|랍스터|새우|오징어|낙지|쭈꾸미|주꾸미|문어|아귀|아구찜|장어|고등어|갈치|전복|굴국|굴보쌈|매운탕|포케|연어|참치|광어|우럭|방어|알탕|꼬막|감바스|봉골레|똠얌|똠양|뿌팟퐁|피시앤칩스|피쉬앤칩스/,
  '면': /국수|냉면|밀면|쫄면|라면|라멘|우동|소바|메밀|파스타|스파게티|짜장|짬뽕|팟타이|분짜|라볶이|비빔면|중국요리|중화요리|반점|까르보나라|봉골레|알리오|야키소바|미고렝|미고랭|락사/,
  '밥': /밥|백반|한정식|정식|도시락|돈부리|규동|카레|(^|[^이])커리|오므라이스|리조또|리소토|포케|기사식당|가정식|나시고렝|나시고랭|오차즈케|(^|\s)죽($|\s)|죽집|본죽|전복죽|가츠동|규동/,
  '국물': /국밥|해장국|순댓국|순대국|미역국|찌개|전골|탕(?!수|후)|육개장|칼국수|잔치국수|쌀국수|라멘|우동|짬뽕|샤브|훠궈|수제비|청국장|닭한마리|나베|똠얌|똠양|락사|바쿠테|수프|스프/,
  '매운거': /매운|마라|떡볶이|라볶이|짬뽕|불닭|닭발|쭈꾸미|주꾸미|낙지|아귀|아구찜|육개장|김치찌개|부대|닭볶음탕|닭도리탕|닭갈비|제육|오징어볶음|찜닭|쫄면|순두부|감자탕|훠궈|알탕|해물찜|똠얌|똠양|깐풍|떡꼬치/,
  '채소': /샐러드|비건|채식|나물|산채|쌈밥|월남쌈|보리밥|비빔밥|포케|사찰음식|채소|야채/,
  '빵': /빵|베이커리|제과|베이글|샌드위치|토스트|크루아상|크로와상|바게트|반미|파니니|브런치|서브웨이|스콘/,
  '구이': /구이|삼겹|목살|항정|숯불|바비큐|바베큐|직화|화로|철판|고기집|고깃집|갈비(?!탕|찜)|곱창|막창|대창|양꼬치|닭꼬치|야키토리|스테이크|그릴/,
  '찜': /찜|조림/,
  '날것': /횟집|회센터|회타운|회식당|(^|\s)회($|\s)|물회|사시미|초밥|스시|오마카세|육회|생굴|게장|포케|사케동|연어|활어|타타키|카르파치오|세비체/,
  '튀김': /튀김|치킨|통닭|후라이드|닭강정|돈까스|돈가스|카츠|텐동|가라아게|탕수육|꿔바로우|감자튀김|유린기|깐풍기|피시앤칩스|피쉬앤칩스|가츠동/,
  '안주': /술집|주점|포차|포장마차|이자카야|호프|맥주|와인|하이볼|전집|파전|족발|보쌈|곱창|막창|대창|닭발|꼬치|야키토리|양꼬치|치킨|통닭|노가리|골뱅이|육회|횟집|회센터|회타운|조개구이|감바스|모츠나베|바비큐|바베큐/,
  '디저트': /디저트|케이크|빙수|아이스크림|젤라또|와플|크로플|도넛|도너츠|푸딩|마카롱|크레페|크레프|아사이|제과|붕어빵|호떡|팬케이크|타르트|쿠키|약과|인절미/,
};
const autoFeats = c => {
  if (!c) return [];
  const hit = s => FEATS.filter(f => FEAT_KEYS[f].test(s));
  const fn = [...new Set([...hit(c.name || ''), ...hit(menusOf(c))])], fc = hit(String(c.category || '').split('>').map(x => x.trim()).filter(x => x && x !== '음식점').join(' '));
  // 이름·기록한 메뉴에서 찾은 게 있으면 그걸 쓰고 카카오 분류에서는 재료(고기·해산물·채소)만 보탬. 그걸로 모르면 분류를 다 씀
  const fs = fn.length ? [...fn, ...fc.filter(f => ['고기', '해산물', '채소'].includes(f))] : fc;
  if (kindsOf(c).includes('술집')) fs.push('안주');
  return FEATS.filter(f => fs.includes(f));
};
const featsOf = c => (c && (Array.isArray(c.feats) ? c.feats : autoFeats(c))) || [];
// 영업 정보(HOURS)는 태그 칩에서 빼고 주소 밑 한 줄로
const hrsOf = c => (c && c.tags || []).filter(t => HOURS.includes(t));
const tagsOnly = c => (c && c.tags || []).filter(t => !HOURS.includes(t));
const hrsLine = c => { const h = hrsOf(c); return h.length ? esc(h.join(' · ')) : '<span style="opacity:.55">+ 영업 정보</span>'; };
// 칩 거르기: 종류·음식 성격은 고른 것 중 하나만 맞으면, 태그는 고른 게 다 맞아야
const passTags = (c, sel) => {
  const a = [...sel], ks = a.filter(t => KINDS.includes(t));
  return (!ks.length || ks.some(k => kindsOf(c).includes(k))) && (fs => !fs.length || fs.some(t => featsOf(c).includes(t)))(a.filter(t => FEATS.includes(t)))
    && a.filter(t => !KINDS.includes(t) && !FEATS.includes(t)).every(t => (c.tags || []).includes(t));
};
"""
rep("const TAGS = ['혼밥 가능',", KIND_JS + "const TAGS = ['혼밥 가능',")
rep("[...mapSel.tags].every(t => (c.tags || []).includes(t))", "passTags(c, mapSel.tags)", 2)
rep("[...listSel.tags].every(t => (c.tags || []).includes(t))", "passTags(c, listSel.tags)")
rep("return (c.tags||[]).includes(f);", "return KINDS.includes(f) ? kindsOf(c).includes(f) : FEATS.includes(f) ? featsOf(c).includes(f) : (c.tags||[]).includes(f);")
rep("const used = new Set(cafes.flatMap(c => c.tags||[]));", "const used = new Set(cafes.flatMap(c => [...(c.tags||[]), ...kindsOf(c), ...featsOf(c)]));", 2)
rep("const list = ['전체','다녀왔어 ♪','또 갈래 ♥','가볼래 ☆', ...TAGS.filter(t => used.has(t))];",
    "const list = ['전체','다녀왔어 ♪','또 갈래 ♥','가볼래 ☆', ...KINDS.filter(t => used.has(t))], list2 = [...FEATS.filter(t => used.has(t)), ...TAGS.filter(t => used.has(t))]; // 첫 줄: 상태·종류, 둘째 줄: 음식·분위기·영업")
# 지도 위 칩 두 줄
rep('<div class="chips" id="mapChips"></div>', '<div class="chips" id="mapChips"></div>\n    <div class="chips" id="mapChips2" style="padding-top:0"></div>')
rep('body.sharemode #mapChips{', 'body.sharemode #mapChips,body.sharemode #mapChips2{')
rep("  $('#mapChips').innerHTML = list.map(t => `<button class=\"chip ${on(t) ? 'on' : ''}\" data-t=\"${esc(t)}\">${esc(t)}</button>`).join('');",
    "  $('#mapChips').innerHTML = list.map(t => `<button class=\"chip ${on(t) ? 'on' : ''}\" data-t=\"${esc(t)}\">${esc(t)}</button>`).join('');\n  $('#mapChips2').innerHTML = list2.map(t => `<button class=\"chip ${on(t) ? 'on' : ''}\" data-t=\"${esc(t)}\">${esc(t)}</button>`).join('');\n  $('#mapChips2').classList.toggle('hidden', !list2.length);")
rep("$('#btnFit').onclick = fitStep;", "$('#mapChips2').onclick = e => $('#mapChips').onclick(e);\n$('#btnFit').onclick = fitStep;")
rep("const tags = ['전체','다녀왔어 ♪','또 갈래 ♥','가볼래 ☆', ...TAGS.filter(t => used.has(t))];",
    "const tags = ['전체','다녀왔어 ♪','또 갈래 ♥','가볼래 ☆', ...KINDS.filter(t => used.has(t))], tags2 = [...FEATS.filter(t => used.has(t)), ...TAGS.filter(t => used.has(t))]; // 첫 줄: 상태·종류, 둘째 줄: 음식·분위기·영업")
# 목록 칩도 두 줄
rep('<div class="seg" id="listChips" style="padding-top:0"></div>', '<div class="seg" id="listChips" style="padding-top:0"></div>\n      <div class="seg" id="listChips2" style="padding-top:0"></div>')
rep("  $('#listChips').innerHTML = tags.map(t => `<button class=\"chip ${on(t)?'on':''}\" data-t=\"${esc(t)}\" style=\"font-size:12px;padding:5px 10px\">${esc(t)}</button>`).join('');",
    "  $('#listChips').innerHTML = tags.map(t => `<button class=\"chip ${on(t)?'on':''}\" data-t=\"${esc(t)}\" style=\"font-size:12px;padding:5px 10px\">${esc(t)}</button>`).join('');\n  $('#listChips2').innerHTML = tags2.map(t => `<button class=\"chip ${on(t)?'on':''}\" data-t=\"${esc(t)}\" style=\"font-size:12px;padding:5px 10px\">${esc(t)}</button>`).join('');\n  $('#listChips2').classList.toggle('hidden', !tags2.length);")
rep("const passList = c => ", "$('#listChips2').onclick = e => $('#listChips').onclick(e);\nconst passList = c => ")
rep("...(c.tags||[]), ...visitsOf(c.id)", "...(c.tags||[]), ...kindsOf(c), ...featsOf(c), ...visitsOf(c.id)")
rep("""">${c.closed?'<span class="tag closedt">'""", """">${kindsOf(c).map(k => '<span class="tag kind">'+esc(k)+'</span>').join('')}${featsOf(c).map(f => '<span class="tag feat">'+esc(f)+'</span>').join('')}${perPerson(c) ? '<span class="tag feat">1인 '+won(perPerson(c))+'</span>' : ''}${c.closed?'<span class="tag closedt">'""", 3)
rep(".tag.wish{background:transparent;color:var(--sub);border:1px dashed var(--sub)}",
    ".tag.wish{background:transparent;color:var(--sub);border:1px dashed var(--sub)}\n.tag.kind{background:var(--acc);color:var(--onacc);font-weight:600}\n.tag.feat{background:transparent;color:var(--softt);box-shadow:inset 0 0 0 1.3px var(--soft)}\n.hrsline{cursor:pointer}")
# 식당 정보 편집: '어떤 곳이에요?' 맨 위에 종류 고르기
rep('<label class="f">어떤 곳이에요?</label>', '<label class="f">어떤 곳이에요? <span class="small" style="font-weight:400">(줄마다 여러 개 골라도 돼요)</span></label>')
rep("""<div class="tagpick" id="cTags">""",
    """<div class="tagpick" id="cKind" style="margin-bottom:10px;padding-bottom:10px;border-bottom:1px dashed var(--line)">${KINDS.map(k => `<button class="chip ${kindsOf(c).includes(k)?'on':''}" data-k="${k}">${k}</button>`).join('')}</div>
    <div class="small" style="margin:0 2px 6px">어떤 음식?</div>
    <div class="tagpick" id="cFeat" style="margin-bottom:10px;padding-bottom:10px;border-bottom:1px dashed var(--line)">${FEATS.map(f => `<button class="chip ${featsOf(c).includes(f)?'on':''}" data-f="${f}">${f}</button>`).join('')}</div>
    <div class="small" style="margin:0 2px 6px">분위기·상황</div>
    <div class="tagpick" id="cTags">""")
# 태그 칩에서 영업 정보 빼기
rep("(c.tags||[]).map(t=>`<span class=\"tag\">${esc(t)}</span>`)", "tagsOnly(c).map(t=>`<span class=\"tag\">${esc(t)}</span>`)", 2)
rep("(c.tags||[]).map(t => `<span class=\"tag\">${esc(t)}</span>`)", "tagsOnly(c).map(t => `<span class=\"tag\">${esc(t)}</span>`)", 2)
# 주소 밑 작은 글씨로 영업 정보 (핀 시트, 공유 화면, 오늘 어디 갈까)
rep("· 방문 기록 ${st.count}개</div></div>", "· 방문 기록 ${st.count}개</div>${hrsOf(c).length ? '<div class=\"subt\">' + esc(hrsOf(c).join(' · ')) + '</div>' : ''}</div>")
rep("${c.category ? ' · ' + esc(c.category.split(' > ').pop()) : ''}</div></div>", "${c.category ? ' · ' + esc(c.category.split(' > ').pop()) : ''}</div>${hrsOf(c).length ? '<div class=\"subt\">' + esc(hrsOf(c).join(' · ')) + '</div>' : ''}</div>", 2)
rep("${st.rating ? ' · ★ ' + st.rating.toFixed(1) : ''}</div>", "${st.rating ? ' · ★ ' + st.rating.toFixed(1) : ''}</div>${hrsOf(c).length ? '<div class=\"subt\">' + esc(hrsOf(c).join(' · ')) + '</div>' : ''}")
# 상세 화면: 분류·전화 줄 바로 밑에 영업 정보, 누르면 바로 고르기
rep("${c.category?`<div class=\"subt\">${esc(c.category.split(' > ').slice(-2).join(' · '))}${c.phone?' · '+esc(c.phone):''}</div>`:''}</div>",
    "${c.category?`<div class=\"subt\">${esc(c.category.split(' > ').slice(-2).join(' · '))}${c.phone?' · '+esc(c.phone):''}</div>`:''}<div class=\"subt hrsline\" id=\"dHrs\">${hrsLine(c)}</div></div>")
rep("\n    <div class=\"myrate\">", "\n    <div class=\"tagpick hidden\" id=\"dHrsPick\" style=\"margin-top:10px\">${HOURS.map(t => `<button class=\"chip ${hrsOf(c).includes(t)?'on':''}\" data-h=\"${esc(t)}\" style=\"font-size:12px;padding:5px 10px\">${esc(t)}</button>`).join('')}</div>\n    <div class=\"myrate\">")
rep("  $('#dSub').onclick = async e => {", """  $('#dHrs').onclick = () => $('#dHrsPick').classList.toggle('hidden');
  $('#dHrsPick').onclick = async e => {
    const b = e.target.closest('.chip'); if (!b) return; const h = b.dataset.h;
    const cc = await patchRec('cafes', id, x => { const s = new Set(x.tags || []); s.has(h) ? s.delete(h) : s.add(h); x.tags = [...TAGS.filter(k => s.has(k)), ...[...s].filter(k => !TAGS.includes(k))]; }); if (!cc) return;
    b.classList.toggle('on', (cc.tags || []).includes(h)); $('#dHrs').innerHTML = hrsLine(cc);
    Sync.soon(); refreshAll();
  };
  $('#dSub').onclick = async e => {""")
rep("""<div class="tagpick" id="cTags">${TAGS.map(t => `<button class="chip ${c.tags.includes(t)?'on':''}" data-t="${esc(t)}">${esc(t)}</button>`).join('')}</div>""",
    """<div class="tagpick" id="cTags">${TAGS.filter(t => !TAGS_OPS.includes(t) && !HOURS.includes(t)).map(t => `<button class="chip ${c.tags.includes(t)?'on':''}" data-t="${esc(t)}">${esc(t)}</button>`).join('')}<div class="small" style="flex-basis:100%;margin:6px 2px 0;padding-top:10px;border-top:1px dashed var(--line)">이용</div>${TAGS_OPS.map(t => `<button class="chip ${c.tags.includes(t)?'on':''}" data-t="${esc(t)}">${esc(t)}</button>`).join('')}</div>""")
rep("$('#cTags').onclick = e => { const b = e.target.closest('.chip'); if (b) b.classList.toggle('on'); };",
    "$('#cTags').onclick = e => { const b = e.target.closest('.chip'); if (b) b.classList.toggle('on'); };\n  $('#cKind').onclick = e => { const b = e.target.closest('.chip'); if (!b) return; b.classList.toggle('on');\n    // 음식 성격을 직접 안 건드렸으면 바뀐 종류에 맞춰 자동값을 다시 보여줌 (술집 → 안주)\n    if (!$('#cFeat').dataset.touched && !Array.isArray(c.feats)) { const ks = [...document.querySelectorAll('#cKind .chip.on')].map(x => x.dataset.k), au = autoFeats({ ...c, kind: ks.length ? ks : undefined }); document.querySelectorAll('#cFeat .chip').forEach(x => x.classList.toggle('on', au.includes(x.dataset.f))); } };\n  $('#cFeat').onclick = e => { const b = e.target.closest('.chip'); if (b) { b.classList.toggle('on'); e.currentTarget.dataset.touched = '1'; } };")
rep("c.tags = [...document.querySelectorAll('#cTags .chip.on')].map(b => b.dataset.t);",
    "c.tags = [...[...document.querySelectorAll('#cTags .chip.on')].map(b => b.dataset.t), ...hrsOf(c)];\n  { const ks = [...document.querySelectorAll('#cKind .chip.on')].map(b => b.dataset.k); if (ks.length) c.kind = ks.length === 1 ? ks[0] : ks; else delete c.kind; }\n  if ($('#cFeat').dataset.touched) { const fs = [...document.querySelectorAll('#cFeat .chip.on')].map(b => b.dataset.f), au = (delete c.feats, autoFeats(c)); if (fs.length !== au.length || fs.some(f => !au.includes(f))) c.feats = fs; }")
# 오늘 어디 갈까: '뭐 먹을까?' 줄
rep("function openPick(){\n  const used = [...new Set(cafes.flatMap(c => c.tags||[]))];",
    "function openPick(){\n  const used = [...new Set(cafes.flatMap(c => c.tags||[]))], usedK = KINDS.filter(k => cafes.some(c => kindsOf(c).includes(k))), usedF = FEATS.filter(f => cafes.some(c => featsOf(c).includes(f)));")
# 공유 링크 '빠르게 고르기'에도 종류
rep("shOpt.photo = false;\n  const used = [...new Set(cafes.flatMap(c => c.tags||[]))];",
    "shOpt.photo = false;\n  const used = [...KINDS.filter(k => cafes.some(c => kindsOf(c).includes(k))), ...FEATS.filter(f => cafes.some(c => featsOf(c).includes(f))), ...new Set(cafes.flatMap(c => c.tags||[]))];")
rep("""${used.length ? `<label class="f">이런 곳이면 좋겠어""",
    """${usedK.length ? `<label class="f">뭐 먹을까? (여러 개 고르면 그중 하나)</label><div class="tagpick">${usedK.map(t => `<button class="chip ${pickOpt.tags.includes(t)?'on':''}" data-tg="${esc(t)}">${esc(t)}</button>`).join('')}</div>` : ''}
    ${usedF.length ? `<label class="f">땡기는 거 (여러 개 고르면 그중 하나)</label><div class="tagpick">${usedF.map(t => `<button class="chip ${pickOpt.tags.includes(t)?'on':''}" data-tg="${esc(t)}">${esc(t)}</button>`).join('')}</div>` : ''}
    ${used.length ? `<label class="f">이런 곳이면 좋겠어""")
rep("if (pickOpt.tags.some(t => !(c.tags||[]).includes(t))) return false;", "if (!passTags(c, pickOpt.tags)) return false;")
rep("if (pickOpt.tags.some(t => !(c.tags || []).includes(t))) continue;", "if (!passTags(c, pickOpt.tags)) continue;")

# ---------------------------------------------------------------
# 5) 글자: 커피로그 → 맛집로그, 카페 → 식당 (꾸미는 말은 맛집)
# ---------------------------------------------------------------
rep('커피로그', '맛집로그', 0)
rep('지도에서 카페·식당 아이콘을', '지도에서 식당 아이콘을')
for a, b in [('나의 카페', '나의 맛집'), ('나의카페', '나의맛집'), ('카페 리스트', '맛집 리스트'), ('AI한테 카페', 'AI한테 맛집'),
             ('내 카페 기록', '내 맛집 기록'), ('카페기록-', '맛집기록-'), ('아직 안 가본 카페**를', '아직 안 가본 맛집**을'),
             ('취향에 맞는 아직 안 가본 카페를', '취향에 맞는 아직 안 가본 맛집을')]:
    rep(a, b, 0)
# 받침 있는 말로 바뀌니 조사도 같이
for a, b in [('카페가', '식당이'), ('카페를', '식당을'), ('카페는', '식당은'), ('카페와', '식당과'), ('카페"와', '식당"과'),
             ('카페로', '식당으로'), ('카페예요', '식당이에요'), ('카페나 ', '식당이나 '), ('카페**를', '식당**을')]:
    if a in s:
        s = s.replace(a, b)
s = s.replace('카페', '식당')
for left in ['커피', '카페', '라떼', '아인슈페너']:
    for m in re.finditer(left, s):
        line = s[max(0, s.rfind('\n', 0, m.start())):s.find('\n', m.start())]
        if 'const THEMES' in line or "n:'" in line or 'MENU_GROUPS' in line or "['디저트·음료'" in line:
            continue
        sys.exit(f'남은 커피 말: {line.strip()[:120]}')

rep("맛집로그는 맛집로그와 같은 주소", "맛집로그는 커피로그와 같은 주소")
rep("// 맛집로그 기록 표 (맛집로그는 cafes/visits)", "// 맛집로그 기록 표 (커피로그는 cafes/visits)")

# ---------------------------------------------------------------
# 6) 버전, 보안 해시(CSP)
# ---------------------------------------------------------------
old_ver = re.search(r'<meta name="app-version" content="([^"]+)">', s).group(1)
rep(f'<meta name="app-version" content="{old_ver}">', f'<meta name="app-version" content="{VERSION}">')
rep(f"const APP_VERSION = '{old_ver}';", f"const APP_VERSION = '{VERSION}';")
scripts = re.findall(r'<script>(.*?)</script>', s, re.S)
if len(scripts) != 2:
    sys.exit(f'인라인 스크립트가 {len(scripts)}개예요')
hashes = ["'sha256-" + base64.b64encode(hashlib.sha256(x.encode('utf-8')).digest()).decode() + "'" for x in scripts]
s, n = re.subn(r"script-src 'self' 'sha256-[^']+' 'sha256-[^']+'", "script-src 'self' " + ' '.join(hashes), s)
if n != 1:
    sys.exit('CSP 줄을 못 찾았어요')

# 위에서 넣은 설명 글이 이름 바꾸기에 같이 바뀐 것 되돌리기 (해시 계산 전에 해야 함)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'index.html').write_text(s, encoding='utf-8')

# sw.js, manifest.json (커피로그 폴더에 있으면 같이)
src_dir = pathlib.Path(SRC).parent
if (src_dir / 'sw.js').exists():
    sw = (src_dir / 'sw.js').read_text(encoding='utf-8')
    sw, a = re.subn(r"const C='cafe-map-v\d+';", "const C='food-map-v1'; // 같은 주소의 커피로그 캐시(cafe-map-*)는 건드리지 않음", sw)
    sw, b = re.subn(r"ks\.filter\(k=>k!==C\)", "ks.filter(k=>k.startsWith('food-map')&&k!==C)", sw)
    if a != 1 or b != 1:
        sys.exit('sw.js 바꿀 곳을 못 찾았어요')
    (OUT / 'sw.js').write_text(sw, encoding='utf-8')
if (src_dir / 'manifest.json').exists():
    import json
    m = json.loads((src_dir / 'manifest.json').read_text(encoding='utf-8'))
    m.update(name='맛집로그', short_name='맛집로그', background_color='#FFF9F5', theme_color='#FFF9F5')
    (OUT / 'manifest.json').write_text(json.dumps(m, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
# 아이콘은 tools/icon.svg 로 그림 (rsvg-convert -w 512 icon.svg), dong.json 은 커피로그 것 그대로
print('ok', len(s), 'bytes', VERSION)
