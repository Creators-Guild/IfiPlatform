# Ifi Instagram feed

Last updated: 2026-11-17

How the home page shows recent Instagram posts from IFI's student unions,
the university and humour accounts: where the posts come from, how they're stored and how
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
  picture and the account name aren't links. Each post has a small tag
  with the account's type: union, student democracy, UiO, media or
  humour (yellow). When the account is connected to its union page on
  this site, an "About Navet →" line under the username links there.
- **Admins** manage the list of accounts under Snippets → "Instagram
  accounts", and can hide a post or add one by hand under "Instagram
  posts". Each account has a type and can be connected to its union page;
  the sync connects it by itself when a union page's social links include
  the account.
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
| `InstagramPostImage` | The 2nd, 3rd … picture of an album post |
| `InstagramAccount` | An account in the feed: username, display name, type, union page, order, active, profile picture, and the last sync's time and error |
| `InstagramPost` | A post: account, link, caption, time, image/video/album, picture, hidden, and whether it was synced or added by hand |
| `InstagramSyncState` | One row: when the access token expires |
| `InstagramAccountRequest` | A visitor's request to add an account: username, type, how it's IFI-related (or why it should be shown anyway), optional email, status, answer, and when it was sent and decided |

- Synced posts belong to the sync: in the admin only **Hidden** can be
  changed. Posts added by hand can be edited freely and are never touched
  by the sync.
- **Seeing a post without Instagram.** On every screen, clicking or
  tapping a post's picture opens a viewer over the page, like reels: one
  post fills the screen and each scroll moves to the next, starting at the
  one you clicked. It goes through every stored post, newest first, not
  only the 12 on the page; the rest load the first time it opens. Each
  post has its caption ("… more" / "less") and date, all the pictures of an album
  (arrows or swipe) and the video itself, which plays with sound and
  loops while it's in view. ↓ ↑
  jump between posts, Esc or a click outside closes it. "Show more"
  opens the viewer too, at the first post that isn't hidden. It sits
  under the heading; phones also have one under the posts, since they
  show the posts stacked.
- **The viewer on bigger screens than a phone.** When there's room, a post
  shows like Instagram on a computer: the picture on the left, and the
  account, the whole caption, the date and the link in a column on the
  right. When there isn't, the caption starts at two lines. "… more" then
  opens the column over the right edge of the picture, if it would cover
  less than about half of it, or under the picture otherwise. Videos
  always open it under, so their controls stay visible.
- **Hiding seen posts.** The viewer remembers which posts you've looked
  at (at least half on screen for a second) and hides them the next time
  it opens, so you only scroll through what's new. A pill at the top of
  the viewer says where you are ("2 / 9 new"), how many are hidden ("3
  seen hidden") and has a switch to show them again; an end card says
  when you've seen everything. "Show more" opens at the first post that
  isn't hidden. The list is saved in
  your browser only (local storage, the newest 500), never on the server,
  and the cookies page says so. The homepage feed itself always shows the
  newest posts. The post you clicked on is always shown, seen or not.
- A video Instagram gives us no file for (often reels with licensed music)
  shows its cover with "Watch on Instagram". A video inside an album shows
  as its cover picture.
- Every stored post keeps its video and album pictures. The sync
  downloads them once, and they're deleted with the post. With today's
  accounts that's about 250 MB of media in total (November 2026: 212
  posts, 16 videos, 96 albums).
- The first account list (the accounts Ifi Creators' Guild follows) was
  added by migration `0164_instagram_accounts`.

## Account requests

Anyone can ask for an account to be added, through the box's last line,
"Run an IFI-related account? Suggest an account to show here →". The page (`instagram/request/`,
`views/instagram_views.py`, `forms.py`, template
`home/instagram_request.html`) has two steps:

1. **Check.** The account must be public and a business or creator
   account, because Meta can't read other accounts. Both boxes are
   required, and the page explains how to switch. "It's related to IFI"
   can be left empty: that's the one rule with exceptions.
2. **Request.** Username (a pasted Instagram address works too), type, how
   it's related to IFI (or, without the IFI box, why it should be shown
   anyway) and an optional email for the answer.

Usernames already in the feed or already requested are refused. A hidden
field catches simple bots, and the whole site takes at most 10 requests
an hour.

Admins answer under Snippets → "Instagram account requests"; the
dashboard shows how many wait. Setting the status to **Approved** adds the
account to the feed (or turns it back on), and its posts appear after
the next sync. **Declined** does nothing more. Either way, a requester who
left an email gets the answer in the language they used, with the
optional answer text. Only the first decision counts: changing it later
doesn't add or remove anything, so remove an account in "Instagram
accounts". The sync deletes decided requests six months after the
decision, as the privacy page says.

## The sync: `sync_instagram_posts`

`management/commands/sync_instagram_posts.py`, using the client in
`integrations/instagram.py`.

- Without `INSTAGRAM_ACCESS_TOKEN` in `.env` it does nothing, so local
  development and tests never contact Meta.
- For each active account it fetches the 12 newest posts, downloads new
  pictures (resized to at most 1080 px), updates captions, and keeps only
  the 12 newest synced posts per account, and none older than a year.
  Older ones and their pictures are deleted, so an account that hasn't
  posted for a year has nothing stored until it posts again.
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
  "… more". Without it the feed shows the covers, captions and "See on
  Instagram", but no viewer, videos or full albums.
- The viewer's posts after the first 12 come from `api/instagram/posts/`
  (`instagram_more_posts` in `views/home_views.py`, template
  `viewer_posts.html`), which the script fetches when the viewer first
  opens.
- One row of posts shows at first: 2 on a laptop (at most about 32rem
  each, centered), 3 or 4 on wide screens, filling the row. On
  phone-sized screens (under 45rem, like the rest of the site's phone
  layout) it's one post per row, with 2 shown at first. "Show more" opens
  the viewer at the next post. Without JavaScript it opens the rest of the
  12 in place instead ("Show less" closes them). Rows are separated by
  space, not lines.
- `seed_dev_data` adds twelve example posts with generated pictures, but
  only without `INSTAGRAM_ACCESS_TOKEN`; with a token, run
  `sync_instagram_posts` for real posts instead.

## Where to change things

| To change | Edit |
| --- | --- |
| Which accounts are shown | Snippets → "Instagram accounts" |
| Hide or add a post | Snippets → "Instagram posts" |
| What is fetched from Meta | `integrations/instagram.py` |
| How posts are stored or cleaned up | `management/commands/sync_instagram_posts.py` |
| How often it runs | `deploy/systemd/sync-instagram-posts.timer` |
| The feed's look | the template and CSS above |
| The request page | `views/instagram_views.py`, `forms.py`, `templates/home/instagram_request.html`, `static/css/06_components/home/instagram_request.css` |
| Answer requests | Snippets → "Instagram account requests" |

Tests are in `tests/test_instagram.py`.
