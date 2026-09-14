# account_app CSS structure

Same ITCSS-by-cascade-order convention as the global tree (see
`ifiplatform/static/css/README.md`) and `ifi_home_app`'s own
(`ifiplatform/apps/ifi_home_app/static/css/README.md`), scaled down to
this app's actual size -- no per-concern subfolders needed yet, just the
two tiers. The numbers are the sitewide canonical ITCSS layer positions,
so this tree starts at 05 rather than renumbering from 01:

```
05_objects/     -- account_layout.css (page shell)
06_components/  -- account_card.css, auth_card.css, profile_dropdown.css
account_base.css
```

`account_base.css` is the entry point, linked from every account-app
template. It bundles `05_objects/account_layout.css`,
`06_components/account_card.css`, and `06_components/auth_card.css` via
`@import`. `profile_dropdown.css` is deliberately NOT in that bundle:
the shared `top_header.html` partial puts the profile dropdown on every
page sitewide, not just this app's, so it is linked once in
`ifi_base.html`'s own `<head>` instead. It stays owned by this app
because this app owns the dropdown.

This app has not adopted the block-per-tier loading described in
`ifiplatform/static/css/README.md` yet -- its templates still each link
`account_base.css` themselves, and it has no base template of its own.
That works and causes no flash of unstyled content (the links sit in
`extra_head`, so they are render-blocking), it is just more repetition
than it needs.

No bundler/manifest -- paths are hardcoded, so moving/renaming/splitting
a file here always means finding and updating every template that
references its old path.
