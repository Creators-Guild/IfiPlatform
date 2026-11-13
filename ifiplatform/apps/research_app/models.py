"""Models for the research. For now only the saved monthly totals.

Design notes: docs/claude_context/research_totals.md"""

from django.db import models


class FrozenTotal(models.Model):
    """One whole-site monthly total, saved once its month is settled (see
    totals.freeze_settled), so deleting an account later can't change it.
    A count only: nothing here says who."""

    month = models.CharField(max_length=7)  # "YYYY-MM", Oslo time
    column = models.CharField(max_length=50)  # from SITE_COLUMNS or GITHUB_COLUMNS
    count = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["month", "column"], name="one_frozen_total_per_month"
            )
        ]

    def __str__(self):
        return f"{self.month} {self.column}: {self.count}"
