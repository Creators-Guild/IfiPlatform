"""Prints monthly whole-site totals for the research as CSV, from the site
database, GitHub and the commit history. Counts only: 1 to 4 are shown as
"<5", and nothing names anyone.

Save it to a file:
    python manage.py research_totals --output totals.csv

Design notes: docs/claude_context/research_totals.md"""

import csv
import re

import requests
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from research_app import github_api
from research_app.totals import (
    github_totals,
    last_complete_month,
    month_of,
    rows,
    site_totals,
)

MONTH_FORMAT = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class Command(BaseCommand):
    """research_totals: see the module docstring."""

    help = (
        "Prints monthly whole-site totals for the research as CSV. Counts "
        "only; 1-4 are shown as <5."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            help="First month, YYYY-MM. Default: the first month with data.",
        )
        parser.add_argument(
            "--until",
            help="Last month, YYYY-MM. Default: the last complete month.",
        )
        parser.add_argument(
            "--no-github",
            action="store_true",
            help="Only the site database; leave out the GitHub columns.",
        )
        parser.add_argument(
            "--repo",
            default="Creators-Guild/IfiPlatform",
            help="GitHub repo as owner/name. Default: %(default)s.",
        )
        parser.add_argument(
            "--output",
            help="Save the CSV to this file instead of printing it.",
        )

    def handle(self, *args, **options):
        for option in ("since", "until"):
            if options[option] and not MONTH_FORMAT.match(options[option]):
                raise CommandError(f"--{option} must look like 2026-11.")

        now = timezone.now()
        site = site_totals(now)
        github = {}
        if not options["no_github"]:
            repo = options["repo"]
            try:
                github = github_totals(
                    github_api.get_issues(repo),
                    github_api.get_pulls(repo),
                    github_api.get_commits(repo),
                )
            except requests.RequestException as error:
                raise CommandError(
                    f"GitHub API failed: {error}. Run with --no-github, or set "
                    "GITHUB_TOKEN if the rate limit was reached."
                ) from error

        last_month = options["until"] or last_complete_month(now)
        first_month = options["since"] or min([*site, *github, last_month])
        if first_month > last_month:
            raise CommandError("--since is after --until.")

        table = rows(
            site,
            github,
            first_month,
            last_month,
            include_github=not options["no_github"],
        )
        if options["output"]:
            with open(options["output"], "w", newline="", encoding="utf-8") as file:
                csv.writer(file, lineterminator="\n").writerows(table)
            self.stdout.write(f"Saved {len(table) - 1} months to {options['output']}.")
        else:
            csv.writer(self.stdout, lineterminator="\n").writerows(table)

        this_month = month_of(now)
        if not options["until"] and any(
            month > last_month for month in [*site, *github]
        ):
            self.stderr.write(
                f"{this_month} is left out because the month isn't over yet. "
                f"Add --until {this_month} to see it.",
                style_func=self.style.WARNING,
            )
