# account_app CSS structure

Same ITCSS-by-cascade-order convention as the global tree (see
`ifiplatform/static/css/README.md`) and `ifi_home_app`'s own
(`ifiplatform/apps/ifi_home_app/static/css/README.md`), scaled down to
this app's actual size -- no per-concern subfolders needed yet, just the
two tiers:

```
01_objects/     -- account_layout.css (page shell)
02_components/  -- account_card.css, auth_card.css, profile_dropdown.css
account_base.css
```

`account_base.css` is the entry point, linked from every account-app
template. It bundles `01_objects/account_layout.css`,
`02_components/account_card.css`, and `02_components/auth_card.css` via
`@import`. `profile_dropdown.css` is linked separately, per-template,
where it's actually used (it also appears on non-account-app pages via
the shared `top_header.html` partial, so it isn't something every
account-app page needs bundled in by default).

No bundler/manifest -- every template hardcodes its own `<link>` tag
path, so moving/renaming/splitting a file here always means finding and
updating every template that references its old path.
