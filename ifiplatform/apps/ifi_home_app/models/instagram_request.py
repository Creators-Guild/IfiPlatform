"""Visitors' requests to show their Instagram account in the homepage's Ifi
Instagram feed (the page at instagram/request/). An admin approves or
declines each one in the "Instagram account requests" snippet; approving
adds the account to the feed, and the requester gets an email if they left
one. sync_instagram_posts deletes decided requests after REQUEST_KEPT.

Design rationale: docs/claude_context/home_instagram.md"""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import models, transaction
from django.template.loader import render_to_string
from django.utils import timezone, translation
from django.utils.translation import gettext as _
from wagtail.admin.panels import FieldPanel, FieldRowPanel

from .instagram import KIND_CHOICES, UNION, InstagramAccount

logger = logging.getLogger(__name__)

PENDING, APPROVED, DECLINED = "pending", "approved", "declined"
# Decided requests (and the email in them) are deleted after this (user,
# 2026-11-17; the privacy page says six months).
REQUEST_KEPT = timedelta(days=180)
# Site-wide: nginx passes no client address, so a per-visitor limit would
# treat every visitor as one.
REQUESTS_PER_HOUR = 10


class InstagramAccountRequest(models.Model):
    """One visitor's request to add an account to the feed."""

    STATUS_CHOICES = [
        (PENDING, "Waiting"),
        (APPROVED, "Approved: add it to the feed"),
        (DECLINED, "Declined"),
    ]

    username = models.CharField(max_length=30)
    kind = models.CharField(
        "type",
        max_length=12,
        choices=KIND_CHOICES,
        default=UNION,
        help_text="What the requester chose. Change it before approving if it's wrong.",
    )
    ifi_related = models.BooleanField(
        "IFI-related",
        default=True,
        help_text="Ticked by the requester. If not, the reason says why it "
        "should be shown anyway.",
    )
    reason = models.TextField(
        max_length=1000,
        help_text="How it's related to IFI, or why it should be shown anyway.",
    )
    contact_email = models.EmailField(blank=True)
    language = models.CharField(
        max_length=5,
        default="nb",
        help_text="The language of the page they used; the answer email uses it.",
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    answer = models.TextField(
        blank=True,
        max_length=1000,
        help_text="Optional. Sent to the requester with the decision, if they "
        "left an email.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    panels = [
        FieldPanel("username", read_only=True),
        FieldRowPanel(
            [
                FieldPanel("ifi_related", read_only=True),
                FieldPanel("contact_email", read_only=True),
            ]
        ),
        FieldPanel("reason", read_only=True),
        FieldPanel("kind"),
        FieldPanel("status"),
        FieldPanel("answer"),
        FieldRowPanel(
            [
                FieldPanel("created_at", read_only=True),
                FieldPanel("decided_at", read_only=True),
            ]
        ),
    ]

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Instagram account request"

    def __str__(self):
        return f"@{self.username}"

    def save(self, *args, **kwargs):
        """The first change away from "Waiting" is the decision: it's dated,
        an approval adds the account, and the requester is told. Later
        changes do neither (remove an account in "Instagram accounts")."""
        before = (
            type(self)
            .objects.filter(pk=self.pk)
            .values_list("status", flat=True)
            .first()
            if self.pk
            else None
        )
        deciding = before == PENDING and self.status != PENDING
        if deciding:
            self.decided_at = timezone.now()
        with transaction.atomic():
            super().save(*args, **kwargs)
            if deciding and self.status == APPROVED:
                self._add_account()
        if deciding:
            self._tell_requester()

    def _add_account(self):
        account, created = InstagramAccount.objects.get_or_create(
            username=self.username, defaults={"kind": self.kind}
        )
        if not created and not account.is_active:
            account.is_active = True
            account.save(update_fields=["is_active"])

    def _tell_requester(self):
        if not self.contact_email:
            return
        with translation.override(self.language):
            subject = _("Your Ifi Instagram request")
            message = render_to_string(
                "home/instagram_request_answer.txt", {"request": self}
            )
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [self.contact_email],
            )
        except OSError as error:  # SMTP errors are OSErrors
            logger.warning("Could not email the answer to %s: %s", self, error)


def waiting_requests():
    """How many requests no admin has answered yet."""
    return InstagramAccountRequest.objects.filter(status=PENDING).count()


def too_many_requests():
    """True when the site got REQUESTS_PER_HOUR requests in the last hour."""
    since = timezone.now() - timedelta(hours=1)
    return (
        InstagramAccountRequest.objects.filter(created_at__gte=since).count()
        >= REQUESTS_PER_HOUR
    )


def delete_old_requests():
    """Deletes requests decided more than REQUEST_KEPT ago; returns how many."""
    cutoff = timezone.now() - REQUEST_KEPT
    deleted, _counts = (
        InstagramAccountRequest.objects.exclude(status=PENDING)
        .filter(decided_at__lt=cutoff)
        .delete()
    )
    return deleted
