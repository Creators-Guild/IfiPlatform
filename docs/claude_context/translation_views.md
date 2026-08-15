# translation/views.py — design notes

Context for future Claude sessions. Not a human-facing doc.

## machine_translate_subtree

Unlike wagtail-localize's own "Translate" button (creates empty
translations, one page/subtree at a time, no content) and "Machine
Translate" button (fills in DeepL content, but only for whichever single
page's translation editor is open), this walks `page` and every
descendant, creates/updates each one's English translation, fills it in
via DeepL, and publishes it — all from one confirm screen. Registered as a
wagtail-admin URL (`wagtail_hooks.py`'s `register_admin_urls`) rather than
under `ifi_home_app/urls.py`, so it inherits wagtail-admin's own
login/session handling the same way wagtail-localize's own views do.

## _clear_stale_glossary_translations

`apply_machine_translation()` skips any segment that already has a
`StringTranslation` — normally right, since an unchanged nb sentence keeps
its existing machine translation instead of burning DeepL quota
re-translating something that would come back identical (segments are
content-addressed by wagtail-localize). The one case that's wrong for: a
sentence containing a glossary term, translated *before* the glossary last
changed — DeepL would now translate it differently. This deletes just
those specific, still-stale, machine-made translations so
`apply_machine_translation()` redoes them; any human-corrected translation
is left untouched regardless of glossary terms.

Case-insensitive matching to match DeepL's own glossary matching (confirmed
empirically: `"Fadderuke"`/`"fadderuke"`/`"FADDERUKE"` in source text all
get matched and normalized to the glossary's defined casing).
