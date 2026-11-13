"""The >OUTPUT magazine issues shown in the homepage's magazine box. Rows
are written by sync_output_magazine from ifiavis.no; admins can only hide
one.

Design rationale: docs/claude_context/home_magazinebox.md"""

from django.db import models


class MagazineIssue(models.Model):
    """One >OUTPUT issue, mirrored from ifiavis.no by sync_output_magazine."""

    sanity_id = models.CharField(
        max_length=64,
        unique=True,
        help_text="The issue's ID on ifiavis.no. The sync matches issues on it.",
    )
    title = models.CharField(max_length=200)
    url = models.URLField(max_length=500, help_text="The issue's page on ifiavis.no.")
    cover_url = models.URLField(
        max_length=500,
        help_text="Cover image on Sanity's image CDN, without a size.",
    )
    issue_date = models.DateField(
        help_text="First day of the month the issue came out."
    )
    hidden = models.BooleanField(
        default=False,
        help_text="Hide this issue from the homepage. The sync never changes this.",
    )
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(
        help_text="Last time the sync found this issue on ifiavis.no."
    )

    class Meta:
        ordering = ["-issue_date", "-pk"]
        verbose_name = ">OUTPUT issue"
        verbose_name_plural = ">OUTPUT issues"

    def __str__(self):
        return self.title

    def cover_src(self, width):
        """The cover at the given pixel width, cropped to 3:4."""
        separator = "&" if "?" in self.cover_url else "?"
        height = round(width * 4 / 3)
        return f"{self.cover_url}{separator}w={width}&h={height}&fit=crop&auto=format"

    @property
    def cover_small(self):
        """The cover for the box's 1x screens."""
        return self.cover_src(400)

    @property
    def cover_large(self):
        """The cover for 2x screens."""
        return self.cover_src(800)
