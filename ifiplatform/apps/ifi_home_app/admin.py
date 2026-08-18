"""Admin registration for ifi_home_app models."""

from django.contrib import admin, messages
from django.utils import timezone
from django.utils.text import slugify

import requests
from wagtail.coreutils import find_available_slug
from wagtail.models import Locale

from .integrations.peoply_api import get_organizations
from .models import StudentUnion
from .models.article.unions import StudentUnionCategoryPage, UnionPage
from .models.event_models import (
    PeoplySyncLog,
    PeoplyOrgsWithoutUnion,
    UnionsWithoutPeoplyOrg,
    UnionsWithStalePeoplyLink,
)

admin.site.register(StudentUnion)


@admin.register(PeoplySyncLog)
class PeoplySyncLogAdmin(admin.ModelAdmin):
    """Read-only, superuser-only audit log of "Sync Peoply now" button
    clicks (event_views.force_sync_peoply_events) -- exists to attribute
    spammy/repeated manual syncs to whoever triggered them, not for
    day-to-day staff use, so even a plain staff user can't see it."""

    list_display = ["user", "triggered_at"]

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class _PeoplyUnionMismatchAdmin(admin.ModelAdmin):
    """Shared base for the three PeoplyUnionMismatch proxies below (see
    their own docstrings, event_models.py, on why they're three separate
    admin entries rather than one combined filterable list). Read-only,
    superuser-only -- rows are never edited/deleted by hand here, only
    check_peoply_union_matches writes the mismatch bookkeeping itself.
    `kind` isn't in list_display -- each proxy's own manager already
    restricts it to a single kind, so the column would be constant."""

    list_display = ["label", "first_seen_at", "last_seen_at", "resolved_at"]
    list_filter = ["resolved_at"]

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UnionsWithoutPeoplyOrg)
class UnionsWithoutPeoplyOrgAdmin(_PeoplyUnionMismatchAdmin):
    """Site UnionPages with no peoply_organization_id and no exact Peoply
    name/urlId match -- never had a link. See check_peoply_union_matches's
    own docstring for the exact-match rule."""


@admin.register(UnionsWithStalePeoplyLink)
class UnionsWithStalePeoplyLinkAdmin(_PeoplyUnionMismatchAdmin):
    """Site UnionPages whose peoply_organization_id no longer matches any
    organization Peoply currently returns -- had a link, now broken.
    sync_peoply_events silently syncs nothing for these (Peoply's /events
    just returns no rows for an unknown organizationId), so this is the
    only thing that would ever surface it."""


@admin.register(PeoplyOrgsWithoutUnion)
class PeoplyOrgsWithoutUnionAdmin(_PeoplyUnionMismatchAdmin):
    """Peoply organizations with no matching UnionPage here at all. The
    only one of the three with an action attached -- creating a stub only
    makes sense in this direction, not the other two."""

    actions = ["create_union_pages_for_missing_orgs"]

    @admin.action(description="Create a draft UnionPage for the selected mismatch(es)")
    def create_union_pages_for_missing_orgs(self, request, queryset):
        # Belt-and-suspenders on top of has_module_permission/
        # has_view_permission already gating who can reach this changelist
        # at all -- actions with no explicit `permissions=` are otherwise
        # shown to anyone who can view the list.
        if not request.user.is_superuser:
            self.message_user(request, "Only superusers can do this.", level=messages.ERROR)
            return

        # queryset is already scoped to kind="missing_org" by this proxy's
        # own manager -- only resolved_at still needs excluding here.
        resolved_skipped = queryset.filter(resolved_at__isnull=False).count()
        targets = list(queryset.filter(resolved_at__isnull=True))

        if not targets:
            self.message_user(
                request, "Nothing to create -- selection had no open mismatch.", level=messages.WARNING
            )
            return

        # Unlike the command's own CommandError (which exits the process),
        # an admin action has to degrade to a message + no-op instead of
        # ever bubbling a stack trace to a 500 page.
        try:
            nb_locale = Locale.objects.get(language_code="nb")
            categories = StudentUnionCategoryPage.objects.live().filter(locale=nb_locale)
            count = categories.count()
            if count != 1:
                self.message_user(
                    request,
                    f"Can't auto-create: expected exactly one live nb StudentUnionCategoryPage, "
                    f"found {count}. Use `python manage.py check_peoply_union_matches "
                    "--create-missing --parent-slug ...` instead.",
                    level=messages.ERROR,
                )
                return
            parent = categories.first()
            orgs_by_id = {org["id"]: org for org in get_organizations()}
        except (requests.RequestException, Locale.DoesNotExist) as exc:
            self.message_user(request, f"Couldn't fetch Peoply's organizations: {exc}", level=messages.ERROR)
            return

        created = []
        gone_from_peoply = []
        for mismatch in targets:
            org = orgs_by_id.get(mismatch.identifier)
            if org is None:
                gone_from_peoply.append(mismatch.label)
                continue

            page = UnionPage(
                title=org["name"],
                slug=find_available_slug(parent, slugify(org["name"])),
                locale=nb_locale,
                peoply_organization_id=org["id"],
                website_url=org.get("websiteUrl") or "",
                status="unknown",
                live=False,  # draft only -- needs editor review before publish
            )
            parent.add_child(instance=page)
            page.save_revision()
            created.append(org["name"])

            mismatch.resolved_at = timezone.now()
            mismatch.save()

        if created:
            self.message_user(
                request,
                f"Created {len(created)} draft UnionPage stub(s): {', '.join(created)}. "
                "Review, fill in, and publish each by hand in wagtail-admin.",
                level=messages.SUCCESS,
            )
        if gone_from_peoply:
            self.message_user(
                request,
                f"{len(gone_from_peoply)} selected mismatch(es) no longer appear on Peoply, skipped: "
                + ", ".join(gone_from_peoply),
                level=messages.WARNING,
            )
        if resolved_skipped:
            self.message_user(
                request,
                f"{resolved_skipped} selected row(s) were already resolved, skipped.",
                level=messages.WARNING,
            )
