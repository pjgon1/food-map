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


VERSION = '2026.11.20-1'

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
          "const TAGS = ['혼밥 가능','가성비','양 많음','웨이팅 있음','예약 추천','데이트','모임·회식','분위기 좋음','조용함','술 한잔','늦게까지','포장 가능','주차 가능','아이랑'];")
rep("const SUBS = [['taste', '맛'], ['mood', '분위기'], ['seat', '자리'], ['pref', '취향']];",
    "const SUBS = [['taste', '맛'], ['value', '가성비'], ['mood', '분위기'], ['service', '서비스']];")
MENU = r"""const MENU_GROUPS = [
  ['국밥·탕', /국밥|해장국|설렁탕|곰탕|갈비탕|감자탕|순대국|순댓국|내장탕|도가니탕|삼계탕|추어탕|매운탕|육개장|소머리|선지|뼈해장|수육국밥|탕$/],
  ['찌개·전골', /찌개|전골|부대|짜글이|순두부|청국장|샤브/],
  ['찜·조림', /찜$|찜닭|아구찜|아귀찜|갈비찜|해물찜|조림|코다리/],
  ['아시안', /쌀국수|팟타이|분짜|반미|나시고랭|미고랭|똠얌|똠양|팟카파오|카오팟|월남쌈|탄두리|커리|카레|^난$/],
  ['면·국수', /칼국수|국수|냉면|막국수|밀면|비빔면|쫄면|수제비|우동|소바|라멘|라면|파스타면/],
  ['중식', /짜장|짬뽕|탕수육|마라|훠궈|양장피|깐풍|유린기|딤섬|샤오롱|만두|볶음밥|고추잡채|꿔바로우|멘보샤|팔보채|양꼬치/],
  ['족발·보쌈', /족발|보쌈|수육|편육/],
  ['초밥·회', /초밥|스시|사시미|오마카세|^회$|모둠회|물회|회덮밥|숙성회|활어|연어|참치/],
  ['해산물', /해물|조개|대게|킹크랩|게장|낙지|쭈꾸미|주꾸미|오징어|문어|새우|전복|생선|갈치|고등어|꽃게|홍합|장어|굴$/],
  ['고기구이', /삼겹|오겹|목살|항정|가브리|갈매기|돼지갈비|소갈비|^갈비$|양념갈비|생갈비|등심|안심|차돌|우삼겹|살치|채끝|토시|갈비살|한우|곱창|막창|대창|숯불|불고기|닭갈비|오리|구이$/],
  ['치킨', /치킨|닭강정|후라이드|프라이드|순살|닭다리|윙/],
  ['돈까스·튀김', /돈까스|돈가스|카츠|커틀릿|가라아게|튀김|텐동|덴뿌라/],
  ['일식', /돈부리|규동|사케동|가츠동|카츠동|오야코동|에비동|부타동|우나동|규카츠|오코노미|타코야키|야키토리|스키야키|나베/],
  ['분식', /떡볶이|김밥|순대|어묵|오뎅|라볶이|쫄볶|주먹밥|컵밥|토스트/],
  ['피자', /피자/],
  ['버거·샌드위치', /버거|샌드위치|샌드$|베이글|핫도그|타코|부리또|브리또/],
  ['파스타·양식', /파스타|스파게티|알리오|까르보|봉골레|라자냐|뇨끼|리조또|스테이크|함박|그라탕|필라프/],
  ['샐러드·브런치', /샐러드|포케|브런치|오믈렛|팬케이크|프렌치\s*토스트|와플/],
  ['밥·백반', /비빔밥|백반|정식|한정식|쌈밥|덮밥|오므라이스|제육|불백|도시락|솥밥|돌솥|정찬|밥$/],
  ['전·부침', /전$|파전|부침|빈대떡|육전|동그랑땡/],
  ['술', /소주|맥주|생맥|하이볼|와인|막걸리|사케|칵테일|위스키|고량주|전통주/],
  ['디저트·음료', /케이크|빙수|아이스크림|젤라또|커피|라떼|아메리카노|에이드|주스|콜라|사이다|음료|마카롱|쿠키|빵|차$/],
];"""
rep_block("const MENU_GROUPS = [", "];\n", MENU + "\n")
rep('placeholder="아인슈페너, 크로플, 소금빵…"', 'placeholder="김치찌개, 돈까스, 냉면…"')
rep('placeholder="아인슈페너, 바스크치즈케이크"', 'placeholder="김치찌개, 계란말이"')
rep('placeholder="바스크치즈케이크, 시즌 라떼…"', 'placeholder="수육, 계절 메뉴…"')
rep('placeholder="맛, 분위기, 자리, 웨이팅… 생각나는 대로"', 'placeholder="맛, 양, 서비스, 웨이팅… 생각나는 대로"')
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
rep_block("  cup: '<svg class=\"ic2\" viewBox=\"0 0 24 24\" aria-hidden=\"true\">", "</svg>',\n",
          "  cup: '<svg class=\"ic2\" viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"M9 5.6c-.6-.8.6-1.4 0-2.3M12.2 5c-.6-.8.6-1.4 0-2.3M15.4 5.6c-.6-.8.6-1.4 0-2.3\" fill=\"none\" stroke=\"#C9B8AC\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M5 11c0-2.9 3.2-4.5 7.2-4.5s7.2 1.6 7.2 4.5z\" fill=\"#fff\" stroke=\"#5B4636\" stroke-width=\"1.1\" stroke-linejoin=\"round\"/><path d=\"M3.6 11h17.2a8.6 8.6 0 0 1-17.2 0z\" fill=\"#FFE3EA\" stroke=\"#5B4636\" stroke-width=\"1.3\" stroke-linejoin=\"round\"/><circle cx=\"9.4\" cy=\"14.6\" r=\".6\" fill=\"#5B4636\"/><circle cx=\"15\" cy=\"14.6\" r=\".6\" fill=\"#5B4636\"/><path d=\"M11.6 15.9q.6.5 1.2 0\" fill=\"none\" stroke=\"#5B4636\" stroke-width=\".8\" stroke-linecap=\"round\"/><circle cx=\"8\" cy=\"15.8\" r=\".8\" fill=\"#FFB3C1\"/><circle cx=\"16.4\" cy=\"15.8\" r=\".8\" fill=\"#FFB3C1\"/></svg>',\n")

# 색 테마: 맛집로그 기본은 '고추장'
rep("const THEMES = [\n", "const THEMES = [\n  {k:'gochujang',n:'고추장',    bg:'#FFF9F5',ink:'#3A221C',sub:'#9C7D73',acc:'#C9472D',onacc:'#fff',soft:'#FCE2D9',softt:'#A63A22',note:'#FDF0EA',heart:'#FCE7EA',heartt:'#C2405E',line:'#F4DDD3',frame:'#fff',ph:'#F6CFC1'},\n")
rep("n:'커피 베이지'", "n:'누룽지'")
rep("n:'바닐라 크림'", "n:'계란말이'")
rep("n:'밤 카페 (다크)'", "n:'심야 식당 (다크)'")
rep("let cur = 'coffee'; try { cur = LS.getItem('theme') || 'coffee'; }", "let cur = 'gochujang'; try { cur = LS.getItem('theme') || 'gochujang'; }")
rep("let th = 'coffee'; try { th = LS.getItem('theme') || 'coffee'; }", "let th = 'gochujang'; try { th = LS.getItem('theme') || 'gochujang'; }")
rep('<meta name="theme-color" content="#FFFDF9">', '<meta name="theme-color" content="#FFF9F5">')

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
