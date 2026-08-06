from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Small per-user extension to Django's stock User model, for state that
    doesn't belong on User itself and doesn't warrant a full custom user
    model (AUTH_USER_MODEL swap). Currently just tracks an in-progress email
    change -- see account_app/views/account_views.py."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    pending_email = models.EmailField(
        blank=True,
        help_text="A new email address awaiting confirmation, if any -- see confirm_email_change_view.",
    )

    def __str__(self):
        return f"Profile({self.user})"
