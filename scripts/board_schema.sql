-- Keystone Fantasy message board. Run once in Supabase: SQL Editor -> New query -> paste -> Run.
-- Anyone with the site URL can read and post (name + message). Nobody can edit or delete from the
-- site; you delete spam in the Supabase dashboard (Table Editor -> posts).

create table if not exists public.posts (
  id          bigint generated always as identity primary key,
  created_at  timestamptz not null default now(),
  name        text not null check (char_length(btrim(name)) between 1 and 40),
  message     text not null check (char_length(btrim(message)) between 1 and 1000),
  parent_id   bigint references public.posts(id) on delete cascade
);
create index if not exists posts_created_at_idx on public.posts (created_at desc);
create index if not exists posts_parent_idx on public.posts (parent_id);

-- Replies nest one level only: a reply to a reply is re-parented to the top-level post.
create or replace function public.posts_flatten_parent() returns trigger language plpgsql as $$
declare grand bigint;
begin
  if new.parent_id is not null then
    select parent_id into grand from public.posts where id = new.parent_id;
    if grand is not null then new.parent_id := grand; end if;
  end if;
  return new;
end $$;
drop trigger if exists posts_flatten_parent on public.posts;
create trigger posts_flatten_parent before insert on public.posts
  for each row execute function public.posts_flatten_parent();

-- Light rate limit: at most 5 posts per name per minute, 60 posts site-wide per minute.
create or replace function public.posts_rate_limit() returns trigger language plpgsql as $$
begin
  if (select count(*) from public.posts where name = new.name and created_at > now() - interval '1 minute') >= 5 then
    raise exception 'Slow down: too many posts in the last minute';
  end if;
  if (select count(*) from public.posts where created_at > now() - interval '1 minute') >= 60 then
    raise exception 'The board is busy, try again in a minute';
  end if;
  return new;
end $$;
drop trigger if exists posts_rate_limit on public.posts;
create trigger posts_rate_limit before insert on public.posts
  for each row execute function public.posts_rate_limit();

-- Row-level security: public read + insert, no update/delete from the site.
alter table public.posts enable row level security;
drop policy if exists "board read"  on public.posts;
drop policy if exists "board post"  on public.posts;
create policy "board read" on public.posts for select to anon using (true);
create policy "board post" on public.posts for insert to anon with check (true);
grant select, insert on public.posts to anon;
