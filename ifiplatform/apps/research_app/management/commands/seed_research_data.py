"""Fills the local database with made-up people, drafts and published
pages over the last four months, so research_totals can be tried by hand,
and prints what research_totals should give for them. Only runs with
DEBUG on. Re-running replaces the earlier fake data.

    python manage.py seed_research_data --output expected.csv
    python manage.py research_totals --no-github --output totals.csv
    python manage.py seed_research_data --remove

Design notes: docs/claude_context/research_totals.md"""

import csv

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from research_app import fake_data
from research_app.totals import last_complete_month, rows, site_totals


class Command(BaseCommand):
    """seed_research_data: see the module docstring."""

    help = (
        "Adds made-up research data to the local database and prints the "
        "totals research_totals should give for it. Only with DEBUG on."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            help="Save the expected totals to this CSV file instead of printing them.",
        )
        parser.add_argument(
            "--remove",
            action="store_true",
            help="Only delete the fake research data.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "seed_research_data only runs with DEBUG on: it adds fake "
                "people and pages, which would end up in the real totals."
            )
        if options["remove"]:
            fake_data.remove()
            self.stdout.write("Removed the fake research data.")
            return

        now = timezone.now()
        fake_data.remove()
        other_months = site_totals(now)
        expected = fake_data.create(now)

        last_month = last_complete_month(now)
        table = rows(expected, {}, min(expected), last_month, include_github=False)
        if options["output"]:
            with open(options["output"], "w", newline="", encoding="utf-8") as file:
                csv.writer(file, lineterminator="\n").writerows(table)
            self.stdout.write(f"Saved the expected totals to {options['output']}.")
        else:
            self.stdout.write("research_totals --no-github should print:")
            csv.writer(self.stdout, lineterminator="\n").writerows(table)

        self.stdout.write(
            'The fake pages are under "Fake research data" in the Wagtail '
            "admin. Delete it all with: python manage.py seed_research_data --remove"
        )
        busy = sorted(month for month in other_months if month <= last_month)
        if busy:
            self.stdout.write(
                self.style.WARNING(
                    f"Your database has other data in {', '.join(busy)}. "
                    "research_totals counts that too, so those months won't match."
                )
            )
