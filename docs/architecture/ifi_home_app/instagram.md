# Ifi Instagram feed

Last updated: 2026-11-13

How the home page shows recent Instagram posts from IFI's student unions
and meme accounts: where the posts come from, how they're stored and how
the feed works. Setting up the Meta side is in
[operations/instagram_setup.md](../../operations/instagram_setup.md).

## What it is

- **Visitors** see "Ifi Instagram" under the news on the home page: the
  12 newest posts in rows, newest first. Each post shows the account, how long ago, the picture and the
  whole caption, and links to the post on Instagram. Meme accounts get a
  yellow "meme" tag.
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
| `InstagramAccount` | An account in the feed: username, display name, official or meme, order, active, profile picture, and the last sync's time and error |
| `InstagramPost` | A post: account, link, caption, time, image/video/album, picture, hidden, and whether it was synced or added by hand |
| `InstagramSyncState` | One row: when the access token expires |

- Synced posts belong to the sync: in the admin only **Hidden** can be
  changed. Posts added by hand can be edited freely and are never touched
  by the sync.
- A video shows its cover picture with a play icon, and an album its first
  picture with an icon. Clicking opens the post on Instagram.
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
  `static/css/06_components/home/home_instagram.css`. No JavaScript.
- All 12 posts are shown, with no scrolling inside the box. Posts are at
  most 16rem wide, and as many sit side by side as fit at that size (up to
  five), with lines only between rows.
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
