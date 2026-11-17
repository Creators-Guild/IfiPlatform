# React islands (Claude plan, draft)

Last updated: 2026-11-17

**Status: draft, parked.** The user wants to add React later and rebuild
some parts with it (2026-11-17). Nothing here is decided. Ask the user
before each decision marked **Decide**. Delete this file when it's built
or dropped.

---

## Goal

Use React for the parts of the site that are really interactive, without
turning the site into a single-page app. Django and Wagtail keep rendering
every page, so the editors, URLs, translations, SEO and the Wagtail admin
stay as they are. React only takes over marked boxes on a page
("islands").

## Today (2026-11-17)

- No Node tooling at all: no `package.json`, no build step in CI or
  `deploy/deploy.sh`.
- 23 plain scripts in `static/js/`, loaded per template with
  `<script src defer>`. The biggest is `home_instagram.js`: the viewer,
  seen posts, layouts, video controls and lazy loading.
- Everything is rendered on the server once; nothing refreshes after page
  load except the Instagram viewer's batch and the sync buttons.
- Translations come from Django's `.po` files; strings that scripts need
  are passed in `data-*` attributes (e.g. the viewer's `data-new`).

## Setup

1. **Bundler: Vite**, with `django-vite` to load its output from
   templates (`{% vite_asset 'islands/main.tsx' %}`). In development, the
   Vite dev server hot-reloads; in production, the build writes hashed
   files and a manifest that `collectstatic` picks up.
   **Decide:** TypeScript or plain JavaScript.
2. **Where the code lives:** one `frontend/` folder at the repo root
   (`package.json`, `vite.config`, `src/islands/<name>/`), building into
   a static folder Django already collects.
3. **Mounting pattern:** a template leaves a placeholder and keeps the
   server-rendered version inside it as the no-JS fallback:

   ```django
   <div data-island="opening-hours" data-props="{{ props_json }}">
       {% include "home/partials/openinghours/openinghours.html" %}
   </div>
   ```

   One small entry script finds every `[data-island]`, loads that island
   (code-split, so a page only downloads what it uses) and calls
   `createRoot(el).render(<Island {...props} />)`. Props come from
   `json_script` or a `data-props` attribute.
4. **Data:** small JSON endpoints next to the existing API routes
   (`api/...` in `ifi_home_app/urls.py`), like `api/instagram/posts/`, but
   returning JSON. Islands fetch them on load or poll them when live data
   matters.
5. **Translations:** keep Django as the source. Either pass each island's
   strings in its props, or expose a JSON catalogue with Django's
   `JavaScriptCatalog` view and a tiny `t()` helper.
   **Decide:** props or catalogue.
6. **Styles:** keep the existing CSS files and class names, so islands
   look like the rest of the site and the CSS rules in `CLAUDE.md` still
   apply. No CSS-in-JS.

## CI and deploy

- **CI** (`.github/workflows/ci.yml`): add Node, `npm ci`, a lint step
  (ESLint/Prettier, like Black for Python), the build, and a test runner
  (Vitest + Testing Library) for the islands.
- **Deploy** (`deploy/deploy.sh`): `npm ci && npm run build` before
  `collectstatic`, or build in CI and ship the output.
  **Decide:** build on the server (needs Node there) or in CI.
- **Docker dev setup:** a Node service running the Vite dev server next to
  Django.

## What to convert, in order

1. **Opening hours** (first, small): badges that update by the minute
   ("Open" → "Card needed" → "Closed") without a reload, which the box
   can't do today. Good test of the whole setup: props from the server,
   translations, no-JS fallback.
2. **The Instagram viewer**: the most state (seen posts, layouts, video
   controls, the sheet, lazy loading). Rebuild behind the same markup and
   endpoints; keep every behaviour the user chose (see
   `docs/claude_context/home_instagram.md`).
3. **Later, if they get more interactive:** the message board slideshow,
   the event and union calendars (`event_calendar.js`,
   `union_calendar.js`), the article editor tools.

Plain scripts that just toggle something (menus, the beta notice) stay as
they are: rebuilding them gains nothing.

## Downsides

- A build step and Node in CI, deploy and the dev container.
- Two languages and two ways of doing things during the switch.
- Bigger first download for pages with islands, unless code-splitting is
  kept tight.

## Open questions for the user

- TypeScript or JavaScript?
- Build on the server or in CI?
- Translations through props or a catalogue?
- Which island first: opening hours (recommended) or the Instagram viewer?
