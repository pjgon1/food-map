-- 맛집로그 서버 칸 (커피로그 표·함수·사진은 그대로 두고 새로 추가만 함)
-- 로그인 계정, 친구(friendships), 아이디(profiles)는 커피로그와 같이 씀

-- 1) 기록 표
create table if not exists public.food_places (
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  id text not null,
  data jsonb not null,
  deleted boolean not null default false,
  updated_at timestamptz not null default now(),
  ver bigint not null default 1,
  primary key (user_id, id)
);
create index if not exists food_places_user_updated on public.food_places (user_id, updated_at);

create table if not exists public.food_visits (
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  id text not null,
  place_id text not null,
  data jsonb not null,
  deleted boolean not null default false,
  updated_at timestamptz not null default now(),
  ver bigint not null default 1,
  primary key (user_id, id)
);
create index if not exists food_visits_user_updated on public.food_visits (user_id, updated_at);

create table if not exists public.food_shares (
  id text primary key,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  title text not null,
  data jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists public.food_user_prefs (
  user_id uuid primary key default auth.uid() references auth.users(id) on delete cascade,
  friend_order jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now(),
  rec_order jsonb, friend_names jsonb, menu_groups jsonb, feed_cfg jsonb,
  constraint food_user_prefs_size check (coalesce(pg_column_size(friend_order), 0) + coalesce(pg_column_size(friend_names), 0) + coalesce(pg_column_size(rec_order), 0) < 50000),
  constraint food_user_prefs_menu_size check (coalesce(pg_column_size(menu_groups), 0) < 60000),
  constraint food_user_prefs_feed_size check (coalesce(pg_column_size(feed_cfg), 0) < 10000)
);

-- 2) 각자 자기 것만 (커피로그와 같은 규칙)
alter table public.food_places enable row level security;
alter table public.food_visits enable row level security;
alter table public.food_shares enable row level security;
alter table public.food_user_prefs enable row level security;

drop policy if exists "own food places" on public.food_places;
create policy "own food places" on public.food_places for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists "own food visits" on public.food_visits;
create policy "own food visits" on public.food_visits for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
drop policy if exists "own food shares read" on public.food_shares;
create policy "own food shares read" on public.food_shares for select to authenticated using (user_id = auth.uid());
drop policy if exists "own food shares insert" on public.food_shares;
create policy "own food shares insert" on public.food_shares for insert to authenticated with check (user_id = auth.uid());
drop policy if exists "own food shares delete" on public.food_shares;
create policy "own food shares delete" on public.food_shares for delete to authenticated using (user_id = auth.uid());
drop policy if exists "own food prefs read" on public.food_user_prefs;
create policy "own food prefs read" on public.food_user_prefs for select to authenticated using (user_id = auth.uid());
drop policy if exists "own food prefs insert" on public.food_user_prefs;
create policy "own food prefs insert" on public.food_user_prefs for insert to authenticated with check (user_id = auth.uid());
drop policy if exists "own food prefs update" on public.food_user_prefs;
create policy "own food prefs update" on public.food_user_prefs for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

revoke all on public.food_places, public.food_visits, public.food_shares, public.food_user_prefs from anon, authenticated;
grant select, insert, update, delete on public.food_places, public.food_visits to authenticated;
grant select, insert, delete on public.food_shares to authenticated;
grant select, insert, update on public.food_user_prefs to authenticated;

-- 3) 저장할 때 시각·버전·크기 한도 (커피로그와 같은 함수 그대로 씀)
drop trigger if exists touch_food_places on public.food_places;
create trigger touch_food_places before insert or update on public.food_places for each row execute function public.touch_updated_at();
drop trigger if exists food_places_ver on public.food_places;
create trigger food_places_ver before insert or update on public.food_places for each row execute function public.guard_ver();
drop trigger if exists food_places_limits on public.food_places;
create trigger food_places_limits before insert or update on public.food_places for each row execute function public.guard_limits('50000', '5000');
drop trigger if exists touch_food_visits on public.food_visits;
create trigger touch_food_visits before insert or update on public.food_visits for each row execute function public.touch_updated_at();
drop trigger if exists food_visits_ver on public.food_visits;
create trigger food_visits_ver before insert or update on public.food_visits for each row execute function public.guard_ver();
drop trigger if exists food_visits_limits on public.food_visits;
create trigger food_visits_limits before insert or update on public.food_visits for each row execute function public.guard_limits('50000', '20000');
drop trigger if exists food_shares_limits on public.food_shares;
create trigger food_shares_limits before insert or update on public.food_shares for each row execute function public.guard_limits('5000000', '1000');

-- 4) 동기화 (앱은 'cafes'/'visits' 이름으로 보내고, 여기서 맛집 표로 넣음)
create or replace function public.food_sync_push(tbl text, rows jsonb)
returns jsonb language plpgsql security invoker set search_path = '' as $f$
declare
  uid uuid := auth.uid(); r jsonb; v bigint; cur record; out jsonb := '[]'::jsonb;
  rid text; base bigint; frc boolean; del boolean; dat jsonb; cid text;
begin
  if uid is null then raise exception 'login required'; end if;
  if tbl not in ('cafes', 'visits') then raise exception 'bad table'; end if;
  if jsonb_typeof(rows) <> 'array' or jsonb_array_length(rows) > 500 then raise exception 'bad rows'; end if;
  for r in select * from jsonb_array_elements(rows) loop
    rid := r->>'id'; base := coalesce((r->>'base')::bigint, 0); frc := coalesce((r->>'force')::boolean, false);
    del := coalesce((r->>'deleted')::boolean, false); dat := coalesce(r->'data', '{}'::jsonb); cid := r->>'cafe_id'; v := null;
    begin
      if rid is null or length(rid) = 0 or length(rid) > 100 then raise exception 'bad id'; end if;
      if tbl = 'cafes' then
        if frc or base > 0 then
          update public.food_places t set data = dat, deleted = del, ver = t.ver + 1
          where t.user_id = uid and t.id = rid and (frc or t.ver = base) returning t.ver into v;
        end if;
        if v is null then
          insert into public.food_places (user_id, id, data, deleted) values (uid, rid, dat, del)
          on conflict (user_id, id) do nothing returning ver into v;
        end if;
        if v is null then select t.ver, t.data, t.deleted, t.updated_at into cur from public.food_places t where t.user_id = uid and t.id = rid; end if;
      else
        if frc or base > 0 then
          update public.food_visits t set data = dat, deleted = del, place_id = coalesce(cid, t.place_id), ver = t.ver + 1
          where t.user_id = uid and t.id = rid and (frc or t.ver = base) returning t.ver into v;
        end if;
        if v is null then
          insert into public.food_visits (user_id, id, place_id, data, deleted) values (uid, rid, coalesce(cid, ''), dat, del)
          on conflict (user_id, id) do nothing returning ver into v;
        end if;
        if v is null then select t.ver, t.data, t.deleted, t.updated_at into cur from public.food_visits t where t.user_id = uid and t.id = rid; end if;
      end if;
      if v is not null then out := out || jsonb_build_array(jsonb_build_object('id', rid, 'ok', true, 'ver', v));
      else out := out || jsonb_build_array(jsonb_build_object('id', rid, 'ok', false, 'ver', cur.ver, 'data', cur.data, 'deleted', cur.deleted, 'updated_at', cur.updated_at));
      end if;
    exception when others then
      out := out || jsonb_build_array(jsonb_build_object('id', rid, 'ok', false, 'err', sqlerrm));
    end;
  end loop;
  return out;
end $f$;

-- 5) 친구 기록 보기 (커피로그 친구 관계 그대로)
create or replace function public.food_friend_records(fid uuid)
returns json language sql stable security definer set search_path = public as $f$
  select case when public.is_friend(auth.uid(), fid::text) then json_build_object(
    'cafes', (select coalesce(json_agg(c.data - 'memo' - 'nextTry'), '[]'::json) from public.food_places c
              where c.user_id = fid and coalesce(c.deleted, false) = false
                and coalesce((c.data->>'hideFriends')::boolean, false) = false),
    'visits', (select coalesce(json_agg(v.data), '[]'::json) from public.food_visits v
               where v.user_id = fid and coalesce(v.deleted, false) = false
                 and coalesce((v.data->>'hideFriends')::boolean, false) = false
                 and not exists (select 1 from public.food_places c where c.user_id = fid and c.id = v.place_id
                                 and coalesce((c.data->>'hideFriends')::boolean, false)))
  ) end;
$f$;

-- 6) 공유 링크 (로그인 없이 보기)
create or replace function public.food_get_share(sid text)
returns table(title text, data jsonb, created_at timestamptz) language sql stable security definer set search_path = public as $f$
  select s.title, s.data, s.created_at from public.food_shares s where s.id = sid and length(sid) between 6 and 64 limit 1
$f$;

-- 7) 사진 저장소 (food-photos): 내 폴더만 쓰기, 친구는 숨기지 않은 방문 기록 사진만 보기
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('food-photos', 'food-photos', false, 5242880, '{image/jpeg}')
on conflict (id) do nothing;

create or replace function public.food_photo_count() returns integer
language sql stable security definer set search_path = public, storage as $f$
  select count(*)::int from storage.objects where bucket_id = 'food-photos' and (storage.foldername(name))[1] = auth.uid()::text
$f$;

create or replace function public.food_friend_photo_ok(objname text) returns boolean
language sql stable security definer set search_path = public as $f$
  with p as (select split_part(objname, '/', 1) as owner,
                    regexp_replace(split_part(objname, '/', 2), '(_t)?\.jpg$', '') as pid)
  select exists (
    select 1 from p join public.food_visits v on v.user_id::text = p.owner
    where public.is_friend(auth.uid(), p.owner)
      and coalesce(v.deleted, false) = false
      and coalesce((v.data->>'hideFriends')::boolean, false) = false
      and (v.data->'photoIds') ? p.pid
      and not exists (select 1 from public.food_places c where c.user_id = v.user_id and c.id = v.place_id
                      and (coalesce(c.deleted, false) or coalesce((c.data->>'hideFriends')::boolean, false)))
  );
$f$;

drop policy if exists "own food photos read" on storage.objects;
create policy "own food photos read" on storage.objects for select to authenticated
  using (bucket_id = 'food-photos' and (storage.foldername(name))[1] = auth.uid()::text);
drop policy if exists "own food photos write" on storage.objects;
create policy "own food photos write" on storage.objects for insert to authenticated
  with check (bucket_id = 'food-photos' and (storage.foldername(name))[1] = auth.uid()::text and public.food_photo_count() < 10000);
drop policy if exists "own food photos update" on storage.objects;
create policy "own food photos update" on storage.objects for update to authenticated
  using (bucket_id = 'food-photos' and (storage.foldername(name))[1] = auth.uid()::text);
drop policy if exists "own food photos delete" on storage.objects;
create policy "own food photos delete" on storage.objects for delete to authenticated
  using (bucket_id = 'food-photos' and (storage.foldername(name))[1] = auth.uid()::text);
drop policy if exists "friends food photos read" on storage.objects;
create policy "friends food photos read" on storage.objects for select to authenticated
  using (bucket_id = 'food-photos' and public.food_friend_photo_ok(name));

-- 8) 함수 실행 권한: 로그인한 사람만 (공유 보기만 누구나)
revoke execute on function public.food_sync_push(text, jsonb) from public, anon;
grant execute on function public.food_sync_push(text, jsonb) to authenticated;
revoke execute on function public.food_friend_records(uuid) from public, anon;
grant execute on function public.food_friend_records(uuid) to authenticated;
revoke execute on function public.food_get_share(text) from public;
grant execute on function public.food_get_share(text) to anon, authenticated;
revoke execute on function public.food_photo_count() from public, anon;
grant execute on function public.food_photo_count() to authenticated;
revoke execute on function public.food_friend_photo_ok(text) from public, anon;
grant execute on function public.food_friend_photo_ok(text) to authenticated;

select 'ok' as result;
