# Setting up the Instagram feed

Last updated: 2026-11-13

The home page's "Ifi Instagram" feed reads other accounts' public posts
through Meta's Graph API, using the Ifi Creators' Guild account
(@ificreatorsguild). This guide covers the setup on Meta's side, getting
the token onto the server, and keeping it working. How the feed itself
works is in
[architecture/ifi_home_app/instagram.md](../architecture/ifi_home_app/instagram.md).

Meta changes its menus and permission names often. The steps below were
right in November 2026; if a menu has moved, Meta's own documentation for
the Instagram Graph API's "Business Discovery" is the source of truth.

## What has to be true

- @ificreatorsguild is a **professional** account (business or creator)
  and is linked to a **Facebook Page**.
- A **Meta app** with Facebook Login for Business has access to it.
- The app has **Advanced Access** (through Meta's App Review) to read
  accounts it doesn't manage. Until then only @ificreatorsguild's own
  posts sync.
- Every account in the feed's list is a **public business or creator
  account**. Personal accounts can't be read. Switching an account to a
  creator account is free (Instagram → Settings → Account type and tools).

## 1. Prepare the Instagram account

1. In Instagram, open @ificreatorsguild → Settings → **Account type and
   tools** → **Switch to professional account**, and pick Creator or
   Business.
2. Create a Facebook Page for Ifi Creators' Guild (it can be almost
   empty), and link the Instagram account to it: Page settings →
   **Linked accounts** → Instagram.

## 2. Create the Meta app

1. Log in at [developers.facebook.com](https://developers.facebook.com)
   with a Facebook account that is an admin of the Page.
2. **Create app**, type **Business**. Add the product **Instagram**, and
   choose the setup that uses **Facebook Login for Business**. Business
   Discovery doesn't exist on the "Instagram Login" setup.
3. Under App settings, fill in the privacy policy URL:
   `https://www.ifiplattform.no/account/privacy_policy`.

## 3. Find the account ID and test

In the app's **Graph API Explorer**:

1. Generate a user token with the permissions `instagram_basic`,
   `pages_show_list` and `pages_read_engagement`.
2. Run `me/accounts`. Note the Page's `id`.
3. Run `<page id>?fields=instagram_business_account`. The `id` that comes
   back is **INSTAGRAM_BUSINESS_ACCOUNT_ID**.
4. Test reading another account:
   `<that id>?fields=business_discovery.username(unioslo_ifi){media.limit(3){caption,media_url,permalink,timestamp}}`.
   Captions, image links and dates should come back. Before App Review,
   this only works for @ificreatorsguild itself.

## 4. Get a token that lasts

A token from the Explorer stops working after an hour. Use one of these:

- **Recommended:** a **system user** token from Meta Business Settings →
  Users → System users. Give the system user the app and the Page, then
  generate a token with the permissions above. It doesn't expire.
- Or exchange the user token for a **long-lived** token (60 days). Then it
  has to be renewed before it runs out (see "Keeping it working").

## 5. Put it on the server

On the server, add both to `/home/ubuntu/IfiPlatform/ifiplatform/.env`:

```bash
INSTAGRAM_ACCESS_TOKEN=<the token>
INSTAGRAM_BUSINESS_ACCOUNT_ID=<the id from step 3>
```

Restart the site (`sudo systemctl restart gunicorn`) and run the first
sync by hand:

```bash
sudo systemctl start sync-instagram-posts.service
journalctl -u sync-instagram-posts.service -n 50
```

After that, the `sync-instagram-posts.timer` runs it every hour from 07:00
to 23:00. The deploy installs the timer.

## 6. App Review

To read the other accounts, request **Advanced Access** for the
permissions above in the app's **App Review**. Meta asks for:

- what the app does (show public posts from IFI's student union accounts
  on the department's student site),
- a short screencast of the feed and the Graph API call,
- sometimes **business verification** of Ifi Creators' Guild.

Until it's approved, accounts other than @ificreatorsguild fail with a
permission error. Their posts can be added by hand in the meantime
(Snippets → "Instagram posts" → Add).

## Keeping it working

- **The token runs out:** a long-lived token lasts 60 days. The sync logs a
  warning a week before, and superusers see a warning on the Wagtail
  dashboard. Make a new token (step 4) and replace it in `.env`.
- **An account fails:** Snippets → "Instagram accounts" shows the last
  error for each account. "Not a business account" or "Invalid user"
  usually means a personal account or a changed username. Ask the account
  to switch to a creator account, fix the username, or add its posts by
  hand.
- **Nothing syncs at all:** check `journalctl -u sync-instagram-posts -e`.
  A permission error on every account usually means the token was revoked
  or App Review access was removed.
