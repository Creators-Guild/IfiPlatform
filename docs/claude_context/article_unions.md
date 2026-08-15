# models/article/unions.py — design notes

Context for future Claude sessions. Not a human-facing doc.

## UnionPage.get_context — the local import

`upcoming_events_for_union` is imported inside the method, not at module
level: `event_models.py` imports `TranslationWarningMixin` (and other
symbols) from the `models.article_models` compatibility shim, which in
turn imports from this module — a module-level import the other way would
be circular.

## StudentUnionCategoryPage.union_groups

Editor-curated groupings (e.g. "Faglige foreninger"/"Sosiale foreninger")
shown above the automatic "All unions" listing. `get_context()`'s own
`unions` queryset still lists every live child `UnionPage` regardless of
grouping — a union placed in a group here isn't removed from that full
listing, the two are independent/additive, not a partition. Reuses
`union_card_block()` (the same "Student Union Card" block used inside
`ArticlePage`'s own body) rather than a second, parallel way of picking a
`UnionPage`.

## StudentUnionCategoryPage.get_context

`program_unions`/`other_unions` are both automatic, not editor-curated:
`program_unions` is every active union with `union_type="program"`;
`other_unions` is every active union that isn't program-specific *and*
isn't already placed in one of `union_groups`' own curated groups/rows —
so a union never ends up listed in "Andre foreninger" alongside its own
more specific section.
