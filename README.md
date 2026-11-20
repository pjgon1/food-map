# 맛집로그

다녀온 식당 사진·후기 기록 지도 → https://pjgon1.github.io/food-map/

커피로그(pjgon1/cafe-map) 코드를 그대로 가져와 식당용으로 바꾼 앱.
커피로그를 고친 뒤 맛집로그에도 반영하려면:

    python3 tools/make_food.py <cafe-map>/index.html .

- 로그인·친구·아이디는 커피로그와 같이 씀 (같은 Supabase 프로젝트)
- 기록·사진·공유·설정은 따로: food_places, food_visits, food_shares, food_user_prefs, food-photos (`tools/food_backend.sql`)
- 같은 주소(pjgon1.github.io)라서 이 기기 저장 칸은 `food:` 이름을 붙여 따로 씀
