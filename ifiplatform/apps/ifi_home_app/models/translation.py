"""SegmentTranslation (the English for one piece of Norwegian text on a page
or snippet) and EnglishSlug (a page's English address part).

Design rationale: docs/claude_context/translation_overlay.md"""

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from wagtail.models import Page

SOURCE_CHOICES = [("deepl", "DeepL"), ("human", "Person")]


class SegmentTranslation(models.Model):
    """One row = "at this place on this page, this Norwegian text is this
    English text". Read and written only through
    translation/stored_translations.py."""

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="+"
    )
    object_id = models.PositiveBigIntegerField()
    segment_path = models.TextField()
    norwegian_text = models.TextField()
    norwegian_hash = models.UUIDField()
    english_text = models.TextField()
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    translated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    has_error = models.BooleanField(default=False)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id", "segment_path", "norwegian_hash"],
                name="unique_segment_translation",
            )
        ]

    def __str__(self):
        return f"{self.segment_path}: {self.english_text[:50]}"


class EnglishSlug(models.Model):
    """The English slug of one page, used in its /en/ address. Its own table
    (not a page field), so the worker can set it without a page revision.
    Read and written only through translation/english_urls.py."""

    page = models.OneToOneField(Page, on_delete=models.CASCADE, related_name="+")
    slug = models.SlugField(max_length=255, allow_unicode=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.slug
