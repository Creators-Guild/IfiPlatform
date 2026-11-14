"""The "Ifi Instagram" feed on the homepage: the curated accounts
(InstagramAccount) and their posts (InstagramPost), either synced by
sync_instagram_posts or added by hand in the admin. InstagramSyncState
remembers when the access token expires, for the admin dashboard.

Design rationale: docs/claude_context/home_instagram.md"""

from datetime import timedelta

from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext as _
from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.admin.panels import FieldPanel, FieldRowPanel

OFFICIAL, MEME = "official", "meme"
SYNCED, MANUAL = "synced", "manual"
IMAGE, VIDEO, ALBUM = "image", "video", "album"
POSTS_KEPT_PER_ACCOUNT = 12


class InstagramAccount(models.Model):
    """An account whose posts may show in the feed."""

    KIND_CHOICES = [(OFFICIAL, "Official"), (MEME, "Meme")]

    username = models.CharField(
        max_length=30, unique=True, help_text="Without @, e.g. 'unioslo_ifi'."
    )
    display_name = models.CharField(max_length=100, blank=True)
    kind = models.CharField(
        max_length=10,
        choices=KIND_CHOICES,
        default=OFFICIAL,
        help_text="Meme accounts get a 'meme' tag in the feed.",
    )
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(
        default=True, help_text="Uncheck to stop syncing and hide its posts."
    )
    profile_picture = models.ImageField(
        upload_to="instagram/avatars/",
        blank=True,
        help_text="Filled in by the sync. Clear it to fetch a new one.",
    )
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(
        max_length=300,
        blank=True,
        help_text="Why the last sync of this account failed, e.g. a personal account.",
    )

    panels = [
        FieldRowPanel([FieldPanel("username"), FieldPanel("display_name")]),
        FieldRowPanel(
            [FieldPanel("kind"), FieldPanel("sort_order"), FieldPanel("is_active")]
        ),
        FieldPanel("profile_picture"),
        FieldPanel("last_synced_at", read_only=True),
        FieldPanel("last_error", read_only=True),
    ]

    class Meta:
        ordering = ["sort_order", "username"]
        verbose_name = "Instagram account"

    def __str__(self):
        return f"@{self.username}"

    @property
    def initials(self):
        """Up to two letters for the avatar when there's no picture."""
        words = (self.display_name or self.username).replace("_", " ").split()
        words = [word for word in words if word[0].isalnum()]
        return "".join(word[0] for word in words[:2]).upper()

    @property
    def url(self):
        """The account's page on Instagram."""
        return f"https://www.instagram.com/{self.username}/"


class InstagramPostForm(WagtailAdminModelForm):  # pylint: disable=too-many-ancestors
    """Synced posts belong to the sync: only 'hidden' can be changed."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.source == SYNCED:
            for name, form_field in self.fields.items():
                if name != "hidden":
                    form_field.disabled = True


class InstagramPost(models.Model):
    """One post in the feed."""

    MEDIA_CHOICES = [(IMAGE, "Image"), (VIDEO, "Video"), (ALBUM, "Album")]
    SOURCE_CHOICES = [(SYNCED, "Synced"), (MANUAL, "Added by hand")]

    account = models.ForeignKey(
        InstagramAccount, on_delete=models.CASCADE, related_name="posts"
    )
    instagram_id = models.CharField(max_length=64, blank=True, editable=False)
    permalink = models.URLField(help_text="The post's address on Instagram.")
    caption = models.TextField(blank=True)
    posted_at = models.DateTimeField()
    media_type = models.CharField(max_length=10, choices=MEDIA_CHOICES, default=IMAGE)
    image = models.ImageField(
        upload_to="instagram/posts/",
        width_field="image_width",
        height_field="image_height",
    )
    image_width = models.PositiveIntegerField(null=True, editable=False)
    image_height = models.PositiveIntegerField(null=True, editable=False)
    hidden = models.BooleanField(
        default=False, help_text="Hide this post from the homepage."
    )
    source = models.CharField(
        max_length=10, choices=SOURCE_CHOICES, default=MANUAL, editable=False
    )

    base_form_class = InstagramPostForm
    panels = [
        FieldPanel("hidden"),
        FieldPanel("account"),
        FieldPanel("permalink"),
        FieldRowPanel([FieldPanel("posted_at"), FieldPanel("media_type")]),
        FieldPanel("image"),
        FieldPanel("caption"),
    ]

    class Meta:
        ordering = ["-posted_at", "-pk"]
        verbose_name = "Instagram post"
        constraints = [
            models.UniqueConstraint(
                fields=["instagram_id"],
                condition=~models.Q(instagram_id=""),
                name="unique_instagram_post_id",
            )
        ]

    def __str__(self):
        return f"@{self.account.username} {self.posted_at:%Y-%m-%d}"

    def age(self, now=None):
        """'45 min', '2 h', '3 d', '1 w', or the date for old posts."""
        delta = (now or timezone.now()) - self.posted_at
        if delta < timedelta(hours=1):
            return _("%(n)s min") % {"n": max(1, int(delta.total_seconds() // 60))}
        if delta < timedelta(days=1):
            return _("%(n)s h") % {"n": int(delta.total_seconds() // 3600)}
        if delta < timedelta(days=7):
            return _("%(n)s d") % {"n": delta.days}
        if delta < timedelta(weeks=9):
            return _("%(n)s w") % {"n": delta.days // 7}
        return timezone.localtime(self.posted_at).strftime("%d.%m.%Y")


@receiver(post_delete, sender=InstagramPost)
def _delete_post_image(sender, instance, **kwargs):  # pylint: disable=unused-argument
    if instance.image:
        instance.image.delete(save=False)


class InstagramSyncState(models.Model):
    """Singleton row (pk=1): what the last sync learnt about the token."""

    token_expires_at = models.DateTimeField(null=True, blank=True)
    checked_at = models.DateTimeField(auto_now=True)

    @classmethod
    def load(cls):
        """The row, or None before the first sync."""
        return cls.objects.filter(pk=1).first()

    @classmethod
    def record_token_expiry(cls, expires_at):
        """Save when the token expires (None: never)."""
        obj, _created = cls.objects.get_or_create(pk=1)
        obj.token_expires_at = expires_at
        obj.save()
        return obj

    def expires_soon(self, days=7):
        """Whether the token expires within `days` days."""
        return bool(
            self.token_expires_at
            and self.token_expires_at - timezone.now() < timedelta(days=days)
        )
