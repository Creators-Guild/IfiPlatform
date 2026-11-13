"""Mirrors the >OUTPUT issues listed on ifiavis.no/utgaver into
MagazineIssue rows, matched on their Sanity ID. Title, link, cover and date
are overwritten when they change on ifiavis; `hidden` is never touched, and
no row is ever deleted (an issue missing from the page keeps showing until
an admin hides it). If the page can't be fetched or read, nothing changes
and the command exits with an error. Runs daily from the
sync-output-magazine systemd timer.

Design rationale: docs/claude_context/home_magazinebox.md"""

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from ifi_home_app.integrations.ifiavis import IfiavisParseError, get_issues
from ifi_home_app.models import MagazineIssue

SYNCED_FIELDS = ("title", "url", "cover_url", "issue_date")


class Command(BaseCommand):
    """See the module docstring."""

    help = "Sync the >OUTPUT magazine issues from ifiavis.no/utgaver."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would change without saving anything.",
        )

    def handle(self, *args, dry_run=False, **options):
        try:
            issues = get_issues()
        except (requests.RequestException, IfiavisParseError) as error:
            raise CommandError(f"Could not read ifiavis.no/utgaver: {error}") from error

        ids = [issue.sanity_id for issue in issues]
        with transaction.atomic():
            created, updated = self._save(issues, dry_run)
        missing = MagazineIssue.objects.exclude(sanity_id__in=ids).count()
        prefix = "Dry run, nothing saved. " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}{len(issues)} issues on ifiavis: {created} new, "
                f"{updated} changed. {missing} stored issues are no longer listed there."
            )
        )

    def _save(self, issues, dry_run):
        """Create or update one row per issue. Returns (created, updated)."""
        existing = MagazineIssue.objects.in_bulk(
            [issue.sanity_id for issue in issues], field_name="sanity_id"
        )
        now = timezone.now()
        created = updated = 0
        for issue in issues:
            values = {field: getattr(issue, field) for field in SYNCED_FIELDS}
            row = existing.get(issue.sanity_id)
            if row is None:
                created += 1
                self.stdout.write(f"New: {issue.title} ({issue.issue_date:%Y-%m})")
                if not dry_run:
                    MagazineIssue.objects.create(
                        sanity_id=issue.sanity_id, last_seen_at=now, **values
                    )
                continue
            changed = [f for f, v in values.items() if getattr(row, f) != v]
            if changed:
                updated += 1
                self.stdout.write(f"Changed: {issue.title} ({', '.join(changed)})")
            if not dry_run:
                for field, value in values.items():
                    setattr(row, field, value)
                row.last_seen_at = now
                row.save(update_fields=[*SYNCED_FIELDS, "last_seen_at"])
        return created, updated
