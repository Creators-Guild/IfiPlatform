# English overlay (translation/*.py, models/translation.py) — design notes

Last updated: 2026-10-12
Covers: ifiplatform/apps/ifi_home_app/translation/page_segments.py, ifiplatform/apps/ifi_home_app/translation/stored_translations.py, ifiplatform/apps/ifi_home_app/translation/english_overlay.py, ifiplatform/apps/ifi_home_app/translation/english_urls.py, ifiplatform/apps/ifi_home_app/models/translation.py, ifiplatform/apps/ifi_home_app/management/commands/update_translation_snapshot.py

Context for future Claude sessions. Not a human-facing doc. The plan and
its decisions: `docs/claude_references/translation_redesign.md`.

## Status

Built in step 1, **inert until the switch-over (step 3)**: English is only
turned on by the English preview mode. The two-tree wagtail-localize setup
(translation/sync.py, status.py, snippets.py, ...) still runs the site.
`english_overlay.translation_status()` is the new per-piece status; it is
not `translation/status.py`'s `translation_status()` (two-tree, removed at
the switch-over).

## Model attribute: `translated_fields`, not `translatable_fields`

wagtail-localize reads a `translatable_fields` attribute itself (expects
TranslatableField objects) and keeps syncing the two trees until the
switch-over. Reusing that name would break it. Every page type and
translatable snippet declares `translated_fields` explicitly (test fails
otherwise). Wagtail's own `title`, `seo_title`, `search_description` are
added for every page by `page_segments.translated_field_names()`; page
types don't list them. `untranslated_block_paths` (stored-path form,
`sitting_members.*.name`) keeps text blocks out, e.g. people's names.
`check_translated_field()` (run by `install()` at startup) rejects choice,
URL, email, slug and non-text fields.

## english_overlay.py

- `TranslatedField` must be a **data descriptor** (get + set): Django puts
  loaded values in `obj.__dict__`, which skips a get-only descriptor. It
  wraps the original attribute (Django's `DeferredAttribute`, or Wagtail's
  StreamField `Creator`), which keeps holding the Norwegian value; `__set__`
  delegates to it and drops the per-object memo (`_english_values`).
- Installed on the **owner** class of each field (`field.model`), so
  `title` goes on Wagtail's `Page`: `get_children()`, breadcrumbs and
  `get_parent()` return plain `Page` objects (found in step 0).
- `english_active()`: `_english` ContextVar and not `_raw`. ContextVars,
  not thread-locals, so async is correct too; always reset with the token
  in `finally`.
- **Copy-back methods** (`refresh_from_db`, `full_clean`, `clean_fields`)
  are wrapped in `raw_norwegian()` on every owner. They do
  `setattr(obj, name, f(getattr(obj, name)))`; with English on that put
  English into the Norwegian slot (step 0 for refresh/deferred loading;
  `full_clean` found in step 1 via `save()`, which calls it first). The
  object then *looks* right, and a later save stores English.
- **Write blocker** (`block_english_writes`): an `execute_wrapper` added to
  every connection (`connection_created` + already-open ones). While
  `english_active()`, INSERT/UPDATE matching a translated table (owners'
  tables + `wagtailcore_revision`, word-boundary regex) raises
  `EnglishWriteBlocked`. Deliberately strict: display and previews never
  save, so it only fires on a bug. Raw-mode saves pass (they read
  Norwegian). Don't "fix" a block by wrapping `save()` in raw mode: that
  would hide the bug and weaken the last safety net.
- `_english_value()` never raises: on any error it logs and shows the
  Norwegian field (a page must never crash because of a translation).
  Writes can't record the error during display (blocked); bad English is
  caught when it's saved (`page_segments.check_english()`).
- `EnglishPreviewMixin.serve_preview()` renders the response **inside**
  `english()`: `TemplateResponse` renders lazily, after the block would
  have ended.

## page_segments.py (the only wagtail-localize importer)

- Stored text = wagtail-localize's `StringValue.data` (escaped, links as
  `<a id="a1">`); hash = `uuid5(HASH_NAMESPACE, text)` with their String
  namespace copied in as our constant. Migrated rows match only because of
  this; a test pins it. Never change either.
- Related-object segments (page/image choosers) are dropped: links and
  images stay Norwegian. Override segments (hrefs) are kept so rich text
  reassembles.
- Every segment value gets a sequential `order`: wagtail-localize's writer
  sorts by it (`organise_template_segments`) and `None` can't be sorted.
- `apply_translations()` writes into `field.to_python(value.get_prep_value())`,
  a fresh copy with the same block ids: wagtail-localize's writer edits in
  place. Cost: chooser blocks load again on the copy (a few queries).
- ListBlocks in the old pre-2.16 format (no item ids) give no pieces
  (wagtail-localize behaviour).

## stored_translations.py

- Rows keyed by the page's **specific** content type + id, so a plain
  `Page` and its `.specific` share rows. Snippets: `get_for_model`.
- `lookup()` memo lives in `obj.__dict__["_english_rows"]`; Wagtail's
  `.specific` copies `__dict__` entries, which is fine (same rows).
- `save_machine()` is `bulk_create(ignore_conflicts=True)`: DeepL never
  overwrites a row, so a person's fix always wins whatever the order.
- `cleanup()` counts the stored object **and** the latest draft as
  current, so drafts never delete rows (also not draft-only pieces an
  editor translated early).
- `rename_segment_path()` takes the historical `apps` so migrations can
  use it.

## english_urls.py

- `request_scope()` memo (ContextVar): all English slugs and the whole page
  tree (`path` → id, slug) once per request, so building many links costs
  no queries. Outside a scope every call queries.
- English slugs must also differ from siblings' **Norwegian** slugs: a page
  without an English slug uses its Norwegian slug under /en/.
- Hooked into `route()`/`get_url_parts()` only at the switch-over (needs
  `WAGTAIL_I18N_ENABLED = False`).

## Rename protection

`translation/translated_fields.json` maps every model's readable place
("body → image → caption") to its stored-path form ("body.*.caption").
`RenameProtectionTests` fails on any difference and prints the
`rename_segment_path(...)` line to put in the migration. Readable form
names block types so struct-field renames are caught even where two block
types share a field name; a block **type** rename keeps the stored form and
moves nothing (the message says so). `manage.py update_translation_snapshot`
rewrites the file.
