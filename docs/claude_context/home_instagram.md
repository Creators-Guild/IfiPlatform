# Homepage Ifi Instagram feed — design rationale

Last updated: 2026-11-13
Covers: ifiplatform/apps/ifi_home_app/integrations/instagram.py, ifiplatform/apps/ifi_home_app/models/instagram.py, ifiplatform/apps/ifi_home_app/management/commands/sync_instagram_posts.py, ifiplatform/apps/ifi_home_app/templates/home/partials/instagram/instagram.html, ifiplatform/apps/ifi_home_app/static/css/06_components/home/home_instagram.css

The human docs (`architecture/ifi_home_app/instagram.md`,
`operations/instagram_setup.md`) explain what it does. This note keeps the
reasons and the traps. The user chose every behaviour on 2026-11-13; don't
change them without asking.

## Why Business Discovery

Instagram has no anonymous API (Basic Display died Dec 2024) and scraping
breaks its terms. Business Discovery reads other *public business/creator*
accounts through one account we own (@ificreatorsguild), Facebook Login
setup only (not the Instagram Login API on graph.instagram.com). Needs App
Review for Advanced Access. Personal accounts (many meme accounts) error,
hence manual posts as a fallback and `InstagramAccount.last_error`.
Third-party sources (not Meta's docs) said recent Graph versions narrow
fields for unowned accounts; the client only asks for basic fields and
skips posts without a usable picture. `INSTAGRAM_GRAPH_VERSION` defaults
to v23.0 and can be changed in `.env`.

## Client traps (`integrations/instagram.py`)

- Graph timestamps are `...+0000`; `fromisoformat` gets `+00:00`.
- Picture: IMAGE → `media_url`; VIDEO → `thumbnail_url` (may be missing,
  then the post is skipped); CAROUSEL_ALBUM → its `media_url` or the first
  child's.
- Errors come back as `{"error": {...}}` (sometimes with 200) →
  `InstagramError` with Meta's message.
- `download()` streams with a 15 MB cap: image links are signed and expire,
  so every picture is copied to `media/instagram/` and resized to 1080 px
  (avatars 150 px) as JPEG.

## Sync rules (user's choices)

- Synced posts are sync-owned: `InstagramPostForm` disables every field but
  `hidden` when `source == synced` (works for any edit, no custom view).
  Manual posts (`source` defaults to manual) are never touched or pruned.
- Keep the 12 newest *synced* posts per account; older rows are deleted
  and the `post_delete` receiver removes their files (disk is 20 GB).
- Profile pictures are only downloaded when empty (Meta's URL changes on
  every call, so there is nothing to compare). Clearing it re-fetches.
- One failing account doesn't stop the others; the command raises
  `CommandError` at the end so the timer's journal shows it.
- No token → print and return 0, so dev/tests/CI never call Meta (tests
  also force the settings empty).
- Token expiry from `debug_token` goes in `InstagramSyncState`; within 7
  days → stderr warning + superuser dashboard panel
  (`admin_dashboard.InstagramTokenPanel`).
- Timer: hourly 07–23 (server timezone; see the Peoply timer's note).

## Feed

- Started as design "E" (a fixed-height box you scroll inside). The user
  then dropped the inner scroll (2026-11-14): the feed shows all 12 posts
  as a plain grid, no max-height, mask or scroll-snap. Don't bring them
  back without asking.
- Post size: `--post-width` on `.home-instagram-feed`, 16rem (user: "way
  smaller" than the first 30rem). Columns (user: more when there's room,
  never smaller posts, equal space around, lines only *between* rows):
  container queries on `.instagram_container` pick 1–5 columns at 36, 53,
  70 and 87rem (n × 16rem + (n + 1) × 1rem + scrollbar), with
  `justify-content: space-evenly` and no column gap, so edge and between
  spaces are equal. The count is explicit, not `auto-fill`, because the
  first row must be known to drop its top border (`:nth-child(-n + N)`).
  Changing `--post-width` means recomputing the thresholds.
- Box: matches the news box and message board, not the side-column boxes
  (user, 2026-11-14): heading outside the card with the news box's own
  `newsbar-heading newsbar-heading--news` classes, then a borderless white
  card (12px radius, the same shadow, 1rem padding). The column container
  queries measure `.home-instagram-card`.
- Meme accounts: yellow tag + dashed picture border. No like/comment
  counts. The All/Official/Memes filter was dropped for now (to_fix.md).
- Placement: in `#home-subcontent` after the news; under 72rem it's a grid
  item with area `instagram` (`home_index_layout.css`).
- `migrations/0164_instagram_accounts.py` holds the initial list (the
  accounts @ificreatorsguild follows, minus a personal account the user
  removed); `gangen_i_tredje` and `digok.memes` are memes.
- The privacy page (`legal/data_processors.html`) got a paragraph: posts
  are copied server-side, visitors' browsers don't contact Instagram.
