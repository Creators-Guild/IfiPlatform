# article_card.css — design history

Covers `ifi_home_app/static/css/02_components/cards/article_card.css`.

## `.articlecard--list`: why plain block flow, not a flex row

The editor-picked `list_style` (`article_body_blocks.html`'s "Show as list
item" toggle, `ArticleBlockStyle.list_style`) collapses a card down to
title left, meta as a right-aligned block, image/intro dropped. The same
class is also applied/removed directly by `article_list_toggle.js` for
the homepage newsbar/articlesbar grids on narrow screens (see
`newsbar_layout.css` and `.articlecard-toggle`) — one shared look for both
"editor picked list style on purpose" and "visitor collapsed this card
themselves", rather than two separately maintained sets of rules for
what's visually identical.

The current layout is title on its own full-width row, date/author below
it in smaller, muted text. It used to be a side-by-side row instead
(title left, meta right-aligned), but the meta column ate enough width
that the title itself had barely any room left and truncated hard (e.g.
"News Artic..."). Plain block flow now (no longer its own flex column) —
the draft badge, h3, meta, and intro are already stacked in that order by
normal document flow, so an outer `display: flex` wasn't actually needed
for the layout itself, only for the row→column switch from the *old*
side-by-side look. Kept as block specifically so this card-wide toggle
animates smoothly on mobile (the `max-height`/`opacity`/`margin`
transitions on `img` and `.articlecard-intro`, and `padding` on
`.articlecard` itself) — switching `display` or `flex-direction` can't be
transitioned by CSS at all, it just snaps instantly, which is what this
avoided.
