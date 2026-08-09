"""Editor mode: on-page style/publish tooling (the toggle, quick-style
panel, per-block mini panel, banner-style panel, Publish/Unpublish buttons)
that lives directly on the live front-end pages, not under /wagtail-admin/.

EditorModeMixin is the one shared authorization rule for it, mixed into
every page type that exposes any of that tooling (ArticlePage, CategoryPage,
ArticleIndexPage, StudentUnionCategoryPage). Before this module existed,
each page type's get_context() and each of article_views.py's 7 save
endpoints (plus save_banner_style) independently called
`<target>.permissions_for_user(user).can_edit()`/`.can_publish()`/
`.can_unpublish()` -- 8+ call sites that had to be kept in sync by hand.
Centralizing here means a future rule change (like account_app's editor
content-ownership terms gate, added below) only has to change in one place
and every page type/endpoint picks it up automatically.

The terms-gate itself is owned by account_app (account_app.permissions.
is_pending_editor) -- this module only ever consumes it as a plain boolean,
it doesn't know anything about Profile/editor_terms_status/nicknames/etc.
Keeping that knowledge on the account_app side (and this module free of it
otherwise) is what "editor mode should stay separated from wagtail [and
account-specific concerns]" means in practice: this module only deals with
Wagtail Page permissions and alias/locale resolution, nothing else."""

from account_app.permissions import is_pending_editor


def editor_mode_allowed(target, user, action):
    """The shared two-part rule behind every editor-mode capability check:
    Wagtail's own page permission for `action` ('edit'/'publish'/
    'unpublish') against `target` (an already alias/locale-resolved page --
    EditorModeMixin.style_target, or ArticlePage.publish_target for publish/
    unpublish specifically), AND that `user` isn't a pending editor who
    hasn't yet responded to the content-ownership terms. Exported (not
    private) so ArticlePage's own publish/unpublish methods -- which need
    publish_target, not the generic style_target every page type gets from
    EditorModeMixin below -- can reuse this same rule instead of
    duplicating it."""
    permissions = target.permissions_for_user(user)
    wagtail_allowed = getattr(permissions, f"can_{action}")()
    return wagtail_allowed and not is_pending_editor(user)


class EditorModeMixin:
    """Mixed into any Page subtype that exposes on-page editor-mode tooling.

    style_target: the page revisions/saves should actually apply to. An
    alias page (e.g. an untranslated locale mirroring another locale's
    page) can't take its own revisions -- Wagtail raises if you try (they're
    an exact, auto-synced copy of their source) -- so edits always go to the
    source instead, which Wagtail then propagates back to the alias
    automatically on publish. Previously only ArticlePage had this
    (verbatim, moved here unchanged); CategoryPage/ArticleIndexPage/
    StudentUnionCategoryPage used to resolve `self` directly with no alias
    handling in save_banner_style, a latent gap fixed by giving them a real
    style_target too.

    can_edit_in_editor_mode: whether `user` may use editor-mode tooling on
    this page at all -- see editor_mode_allowed() above. Publish/unpublish
    aren't part of this mixin: only ArticlePage has that concept at all (the
    other three page types expose no publish controls), so those live as
    ArticlePage's own methods, next to its existing publish_target, reusing
    editor_mode_allowed() directly rather than being forced through a
    style_target every other page type also has to carry."""

    @property
    def style_target(self):
        return self.alias_of.specific if self.alias_of_id else self

    def can_edit_in_editor_mode(self, user):
        return editor_mode_allowed(self.style_target, user, "edit")
