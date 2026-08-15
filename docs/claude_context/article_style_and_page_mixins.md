# models/article/style.py and models/page_mixins.py — design notes

Context for future Claude sessions. Not a human-facing doc.

## ArticleStyle (article/style.py)

Whole-article styling — side padding/alignment/font-size for the body and
title/meta/intro, background color, hero image display, table-of-contents
icon size. Edited on-page via editor mode (`article_quick_style.js`), same
UI pattern as `ArticleBlockStyle`'s per-block overrides. Deliberately not
part of `ArticlePage` (or any Page model), so outside Wagtail's
revision/publish system entirely — styling shouldn't differ between locale
translations of "the same" article, only content should.

Keyed by `translation_key`, exactly like `ArticleBlockStyle` — identical
across every locale copy of one logical article, so every locale
automatically shares one style with no sync code needed. See
`ArticlePage.style` for how a page reaches its row (get-or-create).

`hero_image_box_shadow_offset`/`_blur` are precomputed properties (not left
as a raw multiplier) for the same reason as `_effective_box_style()`'s own
`shadow_offset`/`shadow_blur` in `block_style.py` — 2/8 are `hero_image`'s
original fixed shadow's own offset-y/blur-radius, so `strength=1`
reproduces that exact shadow.

## page_mixins.py

Named `page_mixins`, not `article_mixins`: `TranslationWarningMixin` is
used by `event_models.py`'s `EventPage`/`EventIndexPage` too, not just the
article/union/tool page types.

### EditorModeMixin

Before this module existed, each page type's `get_context()` and each of
`article_views.py`'s save endpoints independently called
`<target>.permissions_for_user(user).can_edit()`/`.can_publish()`/
`.can_unpublish()` — 8+ call sites kept in sync by hand. Centralizing here
means a future rule change (like `account_app`'s editor content-ownership
terms gate) only changes in one place. The terms-gate itself is owned by
`account_app` (`is_pending_editor`) — this module only ever consumes it as
a plain boolean, keeping Wagtail-permission concerns and account-specific
concerns separated.

- `style_target`: the page revisions/saves should actually apply to. An
  alias page (an untranslated locale mirroring another locale's page)
  can't take its own revisions — Wagtail raises if you try — so edits
  always go to the source instead, which Wagtail propagates back to the
  alias automatically on publish.
- Publish/unpublish aren't part of this mixin: only `ArticlePage` has that
  concept (the other three page types expose no publish controls), so
  those live as `ArticlePage`'s own methods, reusing `editor_mode_allowed()`
  directly rather than being forced through a `style_target` every other
  page type also has to carry.
- `can_sync_mirrored_page`: unlike publish/unpublish, this one *is* shared
  by all four page types, since it's just a plain edit action
  (`translation/sync.py`) rather than a Wagtail publish action.

### PageBannerStyle

Used by `CategoryPage` and `ArticleIndexPage` (via `BannerStyleMixin`) —
genuinely shared across both since it's keyed by `translation_key` alone,
not scoped to one Page subclass (unlike `ArticleStyle`, which only
`ArticlePage` uses). Edited on-page via editor mode (`banner_style.js`),
not a Wagtail `FieldPanel` — same reasoning as `ArticleStyle`.

Every color field is blank by default rather than a fixed hex — "never
explicitly chosen yet" and "explicitly chosen" need to stay
distinguishable so the on-page panel's reset-to-default can tell them
apart. Templates apply the actual fallback color at render time.
`banner_width_rem`/`height_rem` blank falls back to a fixed default
(60/14rem in the templates) — unlike `ArticleBlockStyle.width_rem`/
`height_rem`, there's no meaningful "auto" here (the banner isn't a card
sized by its own content).
