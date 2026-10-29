"""Monthly whole-site totals for the research (Phase 1 of the plan). Only
counts: nothing here returns or prints who did something. People are told
apart by ID while counting, and only the number of them is kept.

Design notes: docs/claude_context/research_totals.md"""

from collections import defaultdict
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Min
from wagtail.models import Page, PageLogEntry, Revision

from ifi_home_app.models.event.constants import SITE_TIMEZONE

SMALL_NUMBER_LIMIT = 5  # 1 to 4 are shown as "<5"
DRAFT_ABANDONED_DAYS = 30
SITE_ISSUE_MARKER = "Found on page:"  # the footer's "Report a bug" prefills this
IFI_COMMIT_MARKER = "Made-with: ifi"
GOOD_FIRST_ISSUE_LABEL = "good first issue"
ISSUE_KIND_LABELS = [  # checked in order: a docs issue also has "task"
    ("bug", "bug_reports"),
    ("feature", "feature_requests"),
    ("docs", "docs_issues"),
    ("task", "task_issues"),
]

SITE_COLUMNS = [
    "new_accounts",
    "people_saved_draft",
    "people_published",
    "first_time_publishers",
    "pages_first_published",
    "drafts_never_published",
]

GITHUB_COLUMNS = [
    "issues_opened",
    "bug_reports",
    "feature_requests",
    "docs_issues",
    "task_issues",
    "issues_from_site",
    "good_first_issues_closed",
    "prs_opened",
    "prs_merged",
    "people_opened_pr",
    "first_time_pr_authors_merged",
    "ifi_commits",
    "people_using_ifi",
]


class Tally:
    """Counts per month and column. `add_person` counts each person once
    per month and column."""

    def __init__(self):
        self.counts = defaultdict(lambda: defaultdict(int))
        self.people = defaultdict(lambda: defaultdict(set))

    def add(self, moment, column):
        """Count one more in moment's month."""
        self.counts[month_of(moment)][column] += 1

    def add_person(self, moment, column, person):
        """Count person in moment's month, if not already counted there."""
        self.people[month_of(moment)][column].add(person)

    def result(self):
        """{"YYYY-MM": {column: count}}. The people sets are dropped here."""
        result = defaultdict(dict)
        for month, columns in self.counts.items():
            result[month].update(columns)
        for month, columns in self.people.items():
            for column, people in columns.items():
                result[month][column] = len(people)
        return dict(result)


def month_of(moment):
    """ "YYYY-MM" of an aware datetime, in Oslo time."""
    return moment.astimezone(SITE_TIMEZONE).strftime("%Y-%m")


def last_complete_month(now):
    """The month before now's month, as "YYYY-MM"."""
    first_of_this_month = now.astimezone(SITE_TIMEZONE).replace(day=1)
    return month_of(first_of_this_month - timedelta(days=1))


def months_between(first, last):
    """Every "YYYY-MM" from first to last, both included."""
    year, month = map(int, first.split("-"))
    months = []
    while f"{year:04d}-{month:02d}" <= last:
        months.append(f"{year:04d}-{month:02d}")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months


def show(count):
    """A count as printed: 1 to 4 become "<5", so small groups can't be
    told apart."""
    if 0 < count < SMALL_NUMBER_LIMIT:
        return f"<{SMALL_NUMBER_LIMIT}"
    return str(count)


def site_totals(now):
    """Totals from the site database. Publishing with no user (the Peoply
    sync) doesn't count."""
    tally = Tally()

    for joined in (
        get_user_model()
        .objects.filter(is_active=True)
        .values_list("date_joined", flat=True)
    ):
        tally.add(joined, "new_accounts")

    for user_id, created_at in Revision.page_revisions.filter(
        user__isnull=False
    ).values_list("user_id", "created_at"):
        tally.add_person(created_at, "people_saved_draft", user_id)

    first_publish_by_page = {}
    first_publish_by_user = {}
    for page_id, user_id, timestamp in (
        PageLogEntry.objects.filter(action="wagtail.publish")
        .order_by("timestamp")
        .values_list("page_id", "user_id", "timestamp")
    ):
        first_publish_by_page.setdefault(page_id, (user_id, timestamp))
        if user_id is None:
            continue
        tally.add_person(timestamp, "people_published", user_id)
        first_publish_by_user.setdefault(user_id, timestamp)

    for timestamp in first_publish_by_user.values():
        tally.add(timestamp, "first_time_publishers")
    for user_id, timestamp in first_publish_by_page.values():
        if user_id is not None:
            tally.add(timestamp, "pages_first_published")

    never_published = Page.objects.filter(
        first_published_at__isnull=True, live=False
    ).values_list("id", flat=True)
    cutoff = now - timedelta(days=DRAFT_ABANDONED_DAYS)
    for row in (
        Revision.page_revisions.filter(
            object_id__in=[str(page_id) for page_id in never_published],
            user__isnull=False,
        )
        .values("object_id")
        .annotate(first_saved=Min("created_at"))
    ):
        if row["first_saved"] <= cutoff:
            tally.add(row["first_saved"], "drafts_never_published")

    return tally.result()


def _when(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _is_bot(user):
    return user is None or user.get("type") == "Bot" or user["login"].endswith("[bot]")


def github_totals(issues, pulls, commits):
    """Totals from GitHub API data: the lists from github_api.get_issues,
    get_pulls and get_commits. Bots don't count."""
    tally = Tally()
    _count_issues(tally, issues)
    _count_pulls(tally, pulls)
    _count_commits(tally, commits)
    return tally.result()


def _count_issues(tally, issues):
    for issue in issues:
        if "pull_request" in issue or _is_bot(issue["user"]):
            continue
        opened = _when(issue["created_at"])
        tally.add(opened, "issues_opened")
        labels = {label["name"] for label in issue["labels"]}
        for label, column in ISSUE_KIND_LABELS:
            if label in labels:
                tally.add(opened, column)
                break
        if SITE_ISSUE_MARKER in (issue.get("body") or ""):
            tally.add(opened, "issues_from_site")
        if (
            GOOD_FIRST_ISSUE_LABEL in labels
            and issue.get("state_reason") == "completed"
            and issue.get("closed_at")
        ):
            tally.add(_when(issue["closed_at"]), "good_first_issues_closed")


def _count_pulls(tally, pulls):
    first_merge_by_author = {}
    for pull in sorted(pulls, key=lambda pull: pull["merged_at"] or "~"):
        if _is_bot(pull["user"]):
            continue
        author = pull["user"]["id"]
        opened = _when(pull["created_at"])
        tally.add(opened, "prs_opened")
        tally.add_person(opened, "people_opened_pr", author)
        if pull["merged_at"]:
            merged = _when(pull["merged_at"])
            tally.add(merged, "prs_merged")
            first_merge_by_author.setdefault(author, merged)
    for merged in first_merge_by_author.values():
        tally.add(merged, "first_time_pr_authors_merged")


def _count_commits(tally, commits):
    for commit in commits:
        if IFI_COMMIT_MARKER not in commit["commit"]["message"]:
            continue
        made = _when(commit["commit"]["author"]["date"])
        tally.add(made, "ifi_commits")
        # Commits by an email GitHub doesn't know have no "author" account.
        person = (commit.get("author") or {}).get("id") or commit["commit"]["author"][
            "email"
        ]
        tally.add_person(made, "people_using_ifi", person)


def rows(site, github, first_month, last_month, include_github=True):
    """CSV rows: a header, then one row per month. Missing counts are 0."""
    columns = SITE_COLUMNS + (GITHUB_COLUMNS if include_github else [])
    table = [["month"] + columns]
    for month in months_between(first_month, last_month):
        counts = {**site.get(month, {}), **github.get(month, {})}
        table.append([month] + [show(counts.get(column, 0)) for column in columns])
    return table
