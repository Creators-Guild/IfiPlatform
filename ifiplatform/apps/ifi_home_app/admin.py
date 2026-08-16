"""Admin registration for ifi_home_app models."""

from django.contrib import admin
from .models import StudentUnion
from .models.event_models import PeoplySyncLog

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
