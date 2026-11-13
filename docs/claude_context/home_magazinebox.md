# Homepage >OUTPUT magazine box — design rationale

Last updated: 2026-11-13
Covers: ifiplatform/apps/ifi_home_app/integrations/ifiavis.py, ifiplatform/apps/ifi_home_app/models/magazine.py, ifiplatform/apps/ifi_home_app/management/commands/sync_output_magazine.py, ifiplatform/apps/ifi_home_app/templates/home/partials/magazinebox/magazinebox.html, ifiplatform/apps/ifi_home_app/static/css/06_components/home/home_magazinebox.css, ifiplatform/apps/ifi_home_app/static/js/home_magazinebox.js

The box under the events box on the homepage shows every >OUTPUT issue
(the IFI student magazine, https://www.ifiavis.no/utgaver), one cover at a
time. The heading links to the archive, each cover and caption link to the
issue. The user chose every behaviour below on 2026-11-13 from mockups;
don't change them without asking.

## Where the data comes from: integrations/ifiavis.py

ifiavis.no is Next.js (App Router) + Sanity. No RSS, the WordPress
endpoints 403, and Sanity API access hasn't been asked for yet (to-do in
`docs/to_fix.md`). So `parse_issues()` reads the React Server Components
payload the page embeds:

- The payload is split over `<script>self.__next_f.push([1,"..."])</script>`
  chunks; each chunk is a JSON string literal. Join them **before**
  splitting into rows: a row can straddle two chunks.
- Rows are `"<hex id>:<json>"` lines. Non-JSON rows (`I[...]` module rows,
  text rows) are skipped.
- An issue card is a React element `["$", "$L12", "<sanity _id>", props]`
  with `props.href` starting `/utgaver/`. The React key **is** the Sanity
  document `_id`, used as `MagazineIssue.sanity_id`. Hrefs are irregular
  (`/utgaver/rytme`, `/utgaver/output-lilla`), never build them.
- **Row references.** Next.js streams parts of the tree into later rows
  and leaves `"$L<id>"` in their place: on the real page some cards'
  date div is `"$L14"`, and cards 6–12 are whole rows referenced from the
  grid. `_Tree` resolves these (with a `seen` set against cycles). A
  string like `"$L12"` in an element's *type* slot is never resolved;
  only children are walked.
- Cover: the first descendant element whose `src` is on `cdn.sanity.io`.
  `_cover_base()` drops ifiavis's `w`/`h`/`fit` but keeps `rect=` (their
  crop); `MagazineIssue.cover_src(width)` adds our own size + `auto=format`.
- Title: the first text that isn't the date (the img `alt` is the
  fallback). Date: the text matching "<norsk month> <year>", stored as the
  1st of that month and shown with `|date:"F Y"`, so /en/ gets English
  month names.
- Zero cards, a card without cover/date, or an unknown month raise
  `IfiavisParseError`. That's deliberate: a redesign must fail the sync
  loudly, not look like an empty archive.

Tests build a small page in the same format (`_page()` in
`tests/test_output_magazine.py`, split across two chunks, with an inline
date, a referenced date and a referenced card) instead of committing a copy
of their HTML.

## Sync-owned rows: models/magazine.py, sync_output_magazine

- `update_or_create`-style by `sanity_id`; `title`, `url`, `cover_url`,
  `issue_date` are overwritten every run, `last_seen_at` bumped.
- `hidden` is the only admin-editable field and the sync never writes it.
- Rows are **never deleted**: an issue that drops off the page keeps
  showing until an admin hides it (user's choice). The command prints how
  many stored issues are no longer listed.
- On a fetch/parse error the command raises `CommandError` before writing
  anything.
- Admin: `MagazineIssueViewSet` in `wagtail_hooks.py`, with
  `_SyncOwnedPermissionPolicy` denying add/delete to everyone, superusers
  included (`user_has_permission` is checked before Django's superuser
  shortcut). Other fields are `read_only=True` panels.
- Not `TranslatableMixin`: titles are proper names, no English overlay.
- Timer: `deploy/systemd/sync-output-magazine.timer`, daily 05:30 (the
  backup runs at 05:00). `deploy.sh` installs every unit in that folder.
- `seed_dev_data/magazine.py` seeds three real issues with their real
  Sanity IDs, so a later sync updates them instead of duplicating.

## The box: template, CSS, JS

- Frame copies `.eventsbox_container`'s look (2px `--color-border`, 12px
  radius, the same shadow, 1rem padding) on purpose: the user asked for
  the events box's style. Keep the two in step.
- `.magazinebox_container` is a one-column grid with
  `grid-template-columns: minmax(0, 1fr)` and `min-width: 0` on the strip
  and slides. Without it the strip's intrinsic width (all covers side by
  side) blows the box open; this happened in a mockup.
- Covers: CSS scroll-snap strip (`<ol>`), one slide = cover + caption, so
  swiping works with no JS and the caption always matches the cover.
  Only the first cover is eager; the rest are `loading="lazy"`. `width`/
  `height` attributes reserve the 3:4 space.
- Controls (`[hidden]` until the script runs, since they do nothing
  without it): thin SVG chevrons at both ends, segmented bar between.
  Arrows are hidden on `(hover: none)` and the bar takes the row.
- **Sliding bar** (user's choice for when there are many issues): segments
  are a fixed 14px (+3px gap); `slideBar()` in `home_magazinebox.js`
  translates the row so the current segment is centred, clamped so the
  row never slides past its own ends, and centres the whole row when it
  fits. The mask fades only a side that actually has hidden segments
  (`has-more-before` / `has-more-after` set `--fade-start`/`--fade-end`),
  otherwise the current segment at either end would be faded out.
- Segment buttons are 16px tall with the 4px bar drawn by `::after`, so
  the click target isn't 4px.
- Below 72rem the box is capped at 24rem and centred
  (`home_index_layout.css`), otherwise a full-width 3:4 cover on a tablet
  is taller than the screen.
- Heading text: `{% trans "Ifi magazine" %}` → nb "Ifi-magasinet" (user
  confirmed). The nb .po entries were added by hand and compiled with
  `compilemessages -l nb`: running `makemessages` rewrote ~1,700 lines of
  each .po file (stale line references and old strings), too much churn for
  this change.
