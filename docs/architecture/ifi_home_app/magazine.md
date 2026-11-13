# >OUTPUT magazine box

Last updated: 2026-11-13

How the home page shows the issues of >OUTPUT, the IFI student magazine
published at [ifiavis.no](https://www.ifiavis.no/utgaver): where the issues
come from, how they are stored, and how the box on the home page works.
Read [overview.md](../overview.md) first, and [frontend.md](../frontend.md)
for how templates and CSS are loaded. The events box above it is in
[events.md](events.md#the-home-page-events-box).

## What it is

- **Visitors** see a box under "Happening at Ifi" with one magazine cover
  at a time. They can swipe, use the arrows, or click a segment of the bar
  under the cover to move between issues. Clicking a cover or its title
  opens that issue on ifiavis.no. The heading opens the full archive.
- **Admins** see the stored issues under Snippets → ">OUTPUT issues" in the
  Wagtail admin. The only thing they can change is **Hidden**, which takes
  an issue off the home page.
- A **daily sync** copies the issue list from ifiavis.no. Nobody adds
  issues by hand.

If no issues are stored, the box isn't shown at all. On a fresh local
database, run `seed_dev_data` or `sync_output_magazine` to fill it.

## Where the issues come from

ifiavis.no has no feed or API we can use. The sync reads the page
https://www.ifiavis.no/utgaver and picks out each issue's title, link,
cover image and month. The site is built with Next.js and keeps its content
in Sanity, and the page includes that data in a form the sync can read.
Each issue also has a fixed ID from Sanity, which is how the sync
recognises an issue it has seen before.

This works without anyone's permission, but it breaks if ifiavis redesigns
their site. Asking them for read access to Sanity instead is listed in
[to_fix.md](../../to_fix.md).

Cover images are not copied to our server. The site loads them straight
from Sanity's image service, which resizes them to the size the box needs.

## The model: `MagazineIssue`

`models/magazine.py`, one row per issue, newest first:

| Field | What it holds | Written by |
| --- | --- | --- |
| `sanity_id` | The issue's ID on ifiavis.no | sync, on create |
| `title`, `url`, `cover_url`, `issue_date` | Title, link to the issue, cover image without a size, first day of the issue's month | sync, every run |
| `hidden` | Keeps the issue off the home page | admins only |
| `first_seen_at`, `last_seen_at` | When the sync first and last found the issue | sync |

## The sync: `sync_output_magazine`

`management/commands/sync_output_magazine.py`, using the client in
`integrations/ifiavis.py`.

- **What starts it:** the `sync-output-magazine.timer` systemd timer, every
  day at 05:30 on the server. You can also run it by hand, see
  [management_commands.md](../../operations/management_commands.md#sync_output_magazine).
- **What it does:** reads the issue list, adds new issues, and overwrites
  the title, link, cover and month of known ones if they changed. It never
  changes **Hidden**.
- **When an issue disappears from ifiavis.no:** nothing happens. It keeps
  showing until an admin hides it. The command's last line says how many
  stored issues are no longer listed.
- **When it fails:** if ifiavis.no can't be reached, or the page doesn't
  look as expected (for example after a redesign), the command stops with an
  error before changing anything. The home page keeps showing the issues it
  already has. Check `journalctl -u sync-output-magazine` on the server.

## The box on the home page

- Template: `templates/home/partials/magazinebox/magazinebox.html`,
  included in `home/home_index.html`. The view passes `magazine_issues`
  (all issues not hidden).
- It sits in `aside.home-sidecolumn` together with the events box. On
  narrow screens the order is message board, events, magazine, news.
- Styles: `static/css/06_components/home/home_magazinebox.css`. The frame
  matches the events box on purpose, so change both together.
- Script: `static/js/home_magazinebox.js` runs the arrows and the bar.
  Without JavaScript the covers can still be swiped and every link works;
  only the arrows and bar are missing.
- The bar has one segment per issue. When there are more than fit, it
  slides so the current issue stays in the middle, and fades out at the
  sides that have more.
- On touch screens the arrows are hidden, since you swipe.
- The heading is ">OUTPUT | Ifi magazine", translated to "Ifi-magasinet"
  on Norwegian pages.

## Where to change things

| To change | Edit |
| --- | --- |
| What is read from ifiavis.no | `integrations/ifiavis.py` |
| What the sync stores or overwrites | `management/commands/sync_output_magazine.py` |
| When the sync runs | `deploy/systemd/sync-output-magazine.timer` |
| What admins can edit | `MagazineIssueViewSet` in `wagtail_hooks.py` |
| The box's markup, look or behaviour | the template, CSS and script above |
| Where the box sits on the page | `static/css/05_objects/home_index_layout.css` |

Tests are in `tests/test_output_magazine.py`. They use a small fake copy
of the ifiavis page, so they don't need the internet.
