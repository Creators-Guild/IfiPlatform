# Ifi Instagram feed

Last updated: 2026-11-14

How the home page shows recent Instagram posts from IFI's student unions
and meme accounts: where the posts come from, how they're stored and how
the feed works. Setting up the Meta side is in
[operations/instagram_setup.md](../../operations/instagram_setup.md).

## What it is

- **Visitors** see "Ifi Instagram" under the news on the home page: the
  12 newest posts in rows, newest first, styled like Instagram posts.
  Each post shows the account and how long ago, the picture (no frame,
  never taller than 4:5), and the first two lines of the caption. A long
  caption has a "… more" button that shows the whole caption in place
  (it needs JavaScript; without it the caption stays at two lines). Only
  the "See on Instagram →" link under each post leaves the site; the
  picture and the account name aren't links. Meme accounts get a yellow
  "meme" tag.
- **Admins** manage the list of accounts under Snippets → "Instagram
  accounts", and can hide a post or add one by hand under "Instagram
  posts".
- An **hourly sync** (07:00–23:00) copies the newest posts.

The feed shows the 12 newest visible posts. If there are none, the box
isn't shown.

## Where the posts come from

Instagram has no open API. The sync uses Meta's Graph API through the Ifi
Creators' Guild account, which reads other accounts with **Business
Discovery**. That only works for public business or creator accounts, and
only after Meta's App Review (see the setup guide). Accounts that can't be
read, for example personal accounts, can have their posts added by hand.

Pictures are downloaded and served from our own server
(`media/instagram/`), because Meta's image links expire. Visitors'
browsers only contact Instagram when they open a post, and the privacy
page "Services that handle your data" says so.

## Models

All in `models/instagram.py`:

| Model | What it holds |
| --- | --- |
| `InstagramPostImage` | The 2nd, 3rd … picture of an album post, only for posts the feed shows |
| `InstagramAccount` | An account in the feed: username, display name, official or meme, order, active, profile picture, and the last sync's time and error |
| `InstagramPost` | A post: account, link, caption, time, image/video/album, picture, hidden, and whether it was synced or added by hand |
| `InstagramSyncState` | One row: when the access token expires |

- Synced posts belong to the sync: in the admin only **Hidden** can be
  changed. Posts added by hand can be edited freely and are never touched
  by the sync.
- **Seeing a post without Instagram.** On laptops and wide screens,
  clicking a post's picture opens a viewer over the page, like reels: one
  post fills the screen and each scroll moves to the next, starting at the
  one you clicked. Each post has its caption ("… more" / "less") and date, all the pictures of an album
  (arrows or swipe) and the video itself (click to play, with sound). ↓ ↑
  jump between posts, Esc or a click outside closes it. On phones there's
  no viewer: albums swipe and videos play right in the feed.
- A video Instagram gives us no file for (often reels with licensed music)
  shows its cover with "Watch on Instagram". A video inside an album shows
  as its cover picture.
- Only the 12 posts the feed shows keep their video and album pictures.
  The sync downloads them and deletes them again when a post drops out of
  the 12, so they take about 50–150 MB in total. Other stored posts keep
  just their cover.
- The first account list (the accounts Ifi Creators' Guild follows) was
  added by migration `0164_instagram_accounts`.

## The sync: `sync_instagram_posts`

`management/commands/sync_instagram_posts.py`, using the client in
`integrations/instagram.py`.

- Without `INSTAGRAM_ACCESS_TOKEN` in `.env` it does nothing, so local
  development and tests never contact Meta.
- For each active account it fetches the 12 newest posts, downloads new
  pictures (resized to at most 1080 px), updates captions, and keeps only
  the 12 newest synced posts per account. Older ones and their pictures
  are deleted.
- One account failing doesn't stop the others. The error is saved on the
  account, and the command ends with an error so it shows in the log.
- It checks when the token expires. A week before, it logs a warning and
  superusers see a warning on the Wagtail dashboard.
- Runs from `deploy/systemd/sync-instagram-posts.timer`. See
  [management_commands.md](../../operations/management_commands.md#sync_instagram_posts).

## The feed on the home page

- Template: `templates/home/partials/instagram/instagram.html`, included
  in `home/home_index.html` after the news. Styles:
  `static/css/06_components/home/home_instagram.css`. The script
  `static/js/home_instagram.js` runs the viewer, the album arrows and
  "… more". Without it the feed, the pictures, swiping albums, playing
  videos on phones and "See on Instagram" all still work.
- One row of posts shows at first, up to 4 on wide screens and 3 on a
  laptop. On phone-sized screens (under 45rem, like the rest of the
  site's phone layout) it's one post per row, with 2 shown at first. "Show more" opens the rest of the 12 in place, and "Show
  less" closes them. It's a native toggle, so it works without JavaScript.
  Rows are separated by space, not lines.
- `seed_dev_data` adds four example posts with generated pictures.

## Where to change things

| To change | Edit |
| --- | --- |
| Which accounts are shown | Snippets → "Instagram accounts" |
| Hide or add a post | Snippets → "Instagram posts" |
| What is fetched from Meta | `integrations/instagram.py` |
| How posts are stored or cleaned up | `management/commands/sync_instagram_posts.py` |
| How often it runs | `deploy/systemd/sync-instagram-posts.timer` |
| The feed's look | the template and CSS above |

Tests are in `tests/test_instagram.py`.
