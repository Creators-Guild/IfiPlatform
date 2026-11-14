# Homepage Ifi Instagram feed — design rationale

Last updated: 2026-11-14
Covers: ifiplatform/apps/ifi_home_app/integrations/instagram.py, ifiplatform/apps/ifi_home_app/models/instagram.py, ifiplatform/apps/ifi_home_app/management/commands/sync_instagram_posts.py, ifiplatform/apps/ifi_home_app/templates/home/partials/instagram/instagram.html, ifiplatform/apps/ifi_home_app/templates/home/partials/instagram/media.html, ifiplatform/apps/ifi_home_app/templates/home/partials/instagram/byline.html, ifiplatform/apps/ifi_home_app/static/css/06_components/home/home_instagram.css, ifiplatform/apps/ifi_home_app/static/js/home_instagram.js

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
to v27.0 (what Graph API Explorer used when the setup was tested,
2026-11-14) and can be changed in `.env`. Tested for real then: the
response fields matched `parse_account()` (albums carry `media_url` on the
post itself; picture links end in .webp but are served as JPEG). Business
Discovery needed `instagram_manage_insights` too, and worked for other
accounts while the app was in Development mode.

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
- Keep the 12 newest *synced* posts per account, none older than
  `POST_MAX_AGE` (365 days, user 2026-11-15: quiet accounts kept posts from
  2020); older rows are deleted and the `post_delete` receiver removes
  their files (disk is 20 GB). Posts Meta returns that are already too old
  aren't created at all.
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
- Layout "E with B's spacing" (user, 2026-11-14, from a mockup page; earlier:
  fixed 30rem, fixed 16rem, then an auto-fill grid of up to 6 that felt
  crowded): one row of posts, the rest behind a native `<details>` "Show
  more"/"Show less" toggle (`.home-instagram-toggle`). B's spacing: card
  padding 1.5rem, column gap 2rem, row gap 2.75rem, at most 4 per row.
- The column count is explicit (container `instagram` on
  `.home-instagram-card`: 1, 2 at 54rem, 3 at 96rem, 4 at 128rem. With 1–2
  columns (laptop) posts are capped at 32rem and centered; with 3–4
  (wide screens) they fill the row, ≥ ~30rem, ~43rem on the user's wide
  screen, which they liked. User, 2026-11-15: 19rem too small on a laptop,
  40rem too big there, 26rem "a bit bigger"; capping wide screens too
  "ruined" them. Phones (<45rem) still get full-width posts from the
  @media rule) because the collapsed state must know how many posts make one
  row. Collapsed = `.instagram_container:not(:has(.home-instagram-toggle[open]))`
  hides posts from nth-child 3 (2 on phones and at 2 columns), and the
  wider queries show the 3rd/4th again. The details element is empty; it's
  only the toggle, so all posts stay in one grid and none is lost at any
  width (the mockup's version dropped the 4th at laptop width). The
  template only adds the toggle with more than 2 posts.
- Phones: below 45rem *viewport* (the site's phone breakpoint, where the
  navbar and news headings switch) the feed is always one column with 2
  posts collapsed, whatever the card width (user: at 718px the container
  queries gave 2 columns). That `@media` block comes after the
  `@container` ones so it wins.
- No lines between rows (user, 2026-11-14: they didn't add much); rows are
  separated by space only (now 2.75rem). Earlier versions drew a
  rule in the row gap and clipped the first row's with `clip-path`; don't
  bring it back without asking.
- Pictures cap at 4:5 with `max-height: 125cqi` (the link is an
  inline-size container, so cqi is the post's width).
- Box: matches the news box and message board, not the side-column boxes
  (user, 2026-11-14): heading outside the card with the news box's own
  `newsbar-heading newsbar-heading--news` classes, then a borderless white
  card (12px radius, the same shadow, 1rem padding). The column container
  queries measure `.home-instagram-card`.
- Post style (user, 2026-11-14: "follow Instagram's post style closely"):
  no picture or avatar borders, byline "username • age" (no @), caption
  clamped to 2 lines with the username in bold, and a "… more" `<button>`
  when `InstagramPost.caption_is_long` (over 70 characters or a line
  break; CSS can't detect a clamp, so it's an estimate). It's `hidden` in
  the HTML; `static/js/home_instagram.js` unhides it and makes it expand
  the caption in place (`.is-expanded`: no clamp, `white-space: pre-line`
  so the caption's own line breaks show; keep the caption `<p>` on one
  line in the template or its indentation shows too). "Show more" stays
  the native `<details>` that opens all posts at once (user: not one row
  or one post at a time).
- Navigation (user): only the "See on Instagram →" link
  (`.home-instagram-open`) leaves the site. The picture and the username
  are deliberately not links, so a click on the post never navigates. Pictures are capped at 4:5 with
  `object-fit: cover`, like Instagram's feed (real videos are 9:16).
- Meme accounts: yellow tag only (the dashed border went with the
  Instagram restyle). No like/comment counts. The All/Official/Memes filter was dropped for now (to_fix.md).
- Placement: in `#home-subcontent` after the news; under 72rem it's a grid
  item with area `instagram` (`home_index_layout.css`).
- `migrations/0164_instagram_accounts.py` holds the initial list (the
  accounts @ificreatorsguild follows, minus a personal account the user
  removed); `gangen_i_tredje` and `digok.memes` are memes.
- The privacy page (`legal/data_processors.html`) got a paragraph: posts
  are copied server-side, visitors' browsers don't contact Instagram.

## Videos, albums and the viewer (user's choices, 2026-11-14)

- Goal: let people see posts without an Instagram account. Only the 12
  posts the feed shows (`shown_posts()`, `SHOWN_POSTS`; the view uses the
  same query) get their video (`InstagramPost.video`) and the rest of an
  album (`InstagramPostImage`). `_sync_shown_media()` runs after all
  accounts and frees both from posts that left the 12; the remote URLs
  come from this run only (`self.remote`), so a post whose account failed
  waits for the next run. Measured: 4 videos = 55 MB.
- `download_video()` streams to a temp file (100 MB cap), not memory.
  Album downloads are all-or-nothing per post (partial ones are deleted).
- Meta omits `media_url` for some videos (licensed music): `video` stays
  empty and `media.html` shows the cover + "Watch on Instagram". Videos
  inside albums are stored as their thumbnail.
- Playback: native `<video controls preload="none">`, click to play with
  sound (user). Nothing downloads until someone presses play. A playing video
  pauses when less than half of it is in view (an IntersectionObserver in
  `home_instagram.js`, user: stop when scrolled past), in the viewer and
  the phone feed; closing the viewer pauses all of them too.
- Viewer: design "A2" from a mockup. A native `<dialog>` with all shown
  posts server-rendered as cards in one vertical scroll; opening scrolls to
  the clicked post. Every screen uses it (user, 2026-11-15: phones too):
  the feed shows covers as `<button disabled>` the script enables, so
  without JS there are covers and "See on Instagram" only. On phones the
  viewer posts are edge to edge, full height, with room under the close
  button (which has a dark round background so it shows over a white
  card). `html:has(dialog[open])` locks page scroll; closing pauses videos.
- "Show more" opens the viewer at the first hidden post instead of opening
  the list on screens matching `SHOW_MORE_OPENS_VIEWER` in
  `home_instagram.js`: "all" since 2026-11-15 (user; it was phones only
  first). The native `<details>` still opens the list without JavaScript,
  so the collapsed CSS stays.
- Reels-style (user): each viewer post is the window's height
  (`grid-auto-rows: 100dvh`, card `calc(100dvh - 2rem)`), `scroll-snap-type:
  y mandatory` + `scroll-snap-stop: always`, so a scroll moves exactly one
  post. Media fills the space left (`minmax(0, 1fr)` row, `object-fit:
  contain` on black). Captions start clamped with "… more" / "less" in the
  viewer and the feed (same button, `data-more`/`data-less`); an opened
  caption in the viewer scrolls inside `max-height: 30dvh`.
- Card width follows the picture (user: a fixed 34rem left black bars
  around portrait pictures): the template sets `--ratio: w / h` from the
  stored size (plain digits via `stringformat:'d'`, a localised thousands
  separator would break the CSS), and the width is the height left after
  `--chrome` (~13rem: account line, two caption lines, date, footer) times
  that ratio, at least 22rem so captions stay readable. An opened caption
  or an album picture of another shape can still show thin bars.
- Media markup is in `media.html`, used by the viewer only. Closed-dialog
  copies don't load: images are `loading="lazy"` and
  videos `preload="none"`. When an album comes into view, the script switches
  all its pictures to `loading="eager"`, so the 3rd and later are ready
  before they're swiped to (user saw empty slides). `InstagramPost.pictures` reads stored sizes so
  no file is opened, and skips the album query for unsaved posts (tests).
