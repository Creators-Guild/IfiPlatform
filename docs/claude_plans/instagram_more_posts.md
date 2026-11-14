# Ifi Instagram: more than the newest 12 (Claude plan, draft)

Last updated: 2026-11-15

**Status: draft, parked.** The user wants to ship the current feed first and
maybe expand later (2026-11-15). Nothing here is decided. Delete this file
when it's built or dropped.

---

## Goal

Let visitors see more posts than the newest 12 per account, without the
server's 20 GB disk filling up.

## What costs what (dev data, 2026-11-15)

| Stored | Count | Size |
|---|---|---|
| Rows (caption, link, date) | ~260 | negligible, a few kB each |
| Covers | 260 (12 per account) | 34 MB, ~130 kB each |
| Album pictures | 5 shown albums | 3 MB |
| Videos | 4 shown | 55 MB, ~14 MB each |

The database isn't the cost; media files are, and videos most of all.

## Constraint from Meta

- For accounts we don't own, a single old post can't be fetched by id
  (reported by third-party guides; check). Older posts come from paging an
  account's media through Business Discovery (`media.limit(n)` /
  `after` cursor).
- Picture and video links from Meta expire after a while, so links must be
  refreshed by the sync, not fetched when a visitor asks.
- Asking Meta per visitor would be slow and use up rate limits.

Since 2026-11-15 synced posts older than a year aren't kept at all
(`POST_MAX_AGE`); any "more posts" design starts from that limit.

## Idea: three layers

1. **More rows.** Keep the newest 30–50 posts per account
   (`POSTS_KEPT_PER_ACCOUNT`). Same one request per account per hour, just a
   bigger `media.limit`; it also keeps their media links fresh. Store the
   remote video/album links on the row (they're only in memory today,
   `Command.remote`).
2. **Covers for every stored post.** ~130 kB each: 50 × 23 accounts ≈ 150 MB.
3. **Videos and album pictures on demand, cached with a cap.** A view like
   `/instagram/media/<post>/` downloads from Meta (using the link from the
   last sync) the first time someone opens the post, stores it, serves it
   from our server. A cleanup job deletes the least recently opened files
   when the cache passes a cap (e.g. 2 GB). Visitors never contact Meta, so
   the privacy page stays true. Today's "only the 12 shown get media" rule
   (`shown_posts()`, `_sync_shown_media()`) would become "the 12 shown are
   pre-warmed".

## On the site

- Feed: unchanged (12 newest, "Show more").
- Viewer: when you reach the end, fetch the next batch (an HTML fragment
  view) and append it, like endless scrolling.
- Maybe: a viewer per account (tap a username → that account's posts).

## Downsides

- First view of an old video waits a few seconds while the server fetches it.
- More code: cache view, last-opened tracking, cleanup job, batch loading.
- Meta's platform terms have rules on how long content may be stored: read
  them before keeping months of posts.

## Open questions for the user

- How far back: newest N per account, or last X weeks?
- Covers: all stored posts, or on demand too?
- Cache cap for videos and album pictures.
- Viewer: endless, or stop after a fixed number?
