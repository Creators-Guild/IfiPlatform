"""Made-up site history and GitHub data for trying research_totals by hand
(`manage.py seed_research_data`) and for the tests that check it: people
joining, saving drafts, publishing, opening issues and pull requests over
the last four months, with the cases the totals treat specially. The fake
pages are never live, so they don't show on the site or go to DeepL.

Design notes: docs/claude_context/research_totals.md"""

from datetime import datetime, timedelta, timezone as dt_timezone

from django.contrib.auth import get_user_model
from wagtail.models import Page, PageLogEntry, Revision

from ifi_home_app.models.event.constants import SITE_TIMEZONE
from research_app.totals import GITHUB_COLUMNS, SITE_COLUMNS, month_of

USERNAME_PREFIX = "fake-research-"
PARENT_SLUG = "fake-research-data"

# What the totals should be, worked out by hand from create() and github()
# below. Months back (4 = four months ago) -> counts in column order.
# Site: new_accounts, people_saved_draft, people_published,
# first_time_publishers, pages_first_published, drafts_never_published.
# Person 13's drafts from 29 and 31 days ago come on top (see
# expected_site()).
EXPECTED_SITE = {
    4: [6, 6, 5, 5, 7, 5],
    3: [3, 2, 1, 0, 0, 1],
    2: [0, 1, 1, 1, 0, 0],
    1: [5, 6, 6, 5, 6, 0],
}
# GitHub: issues_opened, bug_reports, feature_requests, docs_issues,
# task_issues, issues_from_site, good_first_issues_closed, prs_opened,
# prs_merged, people_opened_pr, first_time_pr_authors_merged, ifi_commits,
# people_using_ifi.
EXPECTED_GITHUB = {
    4: [6, 5, 0, 0, 0, 5, 0, 5, 5, 5, 5, 5, 3],
    3: [12, 0, 5, 1, 6, 0, 0, 2, 0, 2, 0, 0, 0],
    2: [0, 0, 0, 0, 0, 0, 5, 0, 1, 0, 0, 1, 1],
    1: [6, 1, 0, 5, 0, 0, 0, 6, 6, 6, 5, 6, 5],
}


def _year_month(now, months_back):
    local = now.astimezone(SITE_TIMEZONE)
    months = local.year * 12 + local.month - 1 - months_back
    return months // 12, months % 12 + 1


def _day(now, months_back):
    """12:00 Oslo time on the 10th, months_back months before now's month."""
    year, month = _year_month(now, months_back)
    return datetime(year, month, 10, 12, tzinfo=SITE_TIMEZONE)


def _late_last_day(now, months_back):
    """23:30 UTC on the last day of the month: already the next month in
    Oslo."""
    year, month = _year_month(now, months_back - 1)
    return datetime(year, month, 1, tzinfo=dt_timezone.utc) - timedelta(minutes=30)


class _FakeSite:
    def __init__(self):
        root = Page.get_first_root_node()
        # Under the tree root, outside every site, so no address reaches it.
        self.parent = root.add_child(
            instance=Page(title="Fake research data", slug=PARENT_SLUG, live=False)
        )
        self.people = {}
        self.pages = {}

    def join(self, number, when, verified=True):
        """Makes fake person `number`. They can't log in."""
        self.people[number] = get_user_model().objects.create_user(
            username=f"{USERNAME_PREFIX}{number:02d}",
            password=None,
            date_joined=when,
            is_active=verified,
        )

    def _page(self, name):
        if name not in self.pages:
            self.pages[name] = self.parent.add_child(
                instance=Page(title=f"Fake {name}", slug=name, live=False)
            )
        return self.pages[name]

    def draft(self, name, person, when):
        """Saves a page version. person=None: done by code."""
        page = self._page(name)
        user = self.people.get(person)
        revision = page.save_revision(user=user, clean=False)
        Revision.objects.filter(pk=revision.pk).update(created_at=when)
        return page, revision, user

    def publish(self, name, person, when):
        """Writes the rows Wagtail's publish would, but leaves the page
        offline. person=None: the Peoply sync."""
        page, revision, user = self.draft(name, person, when)
        PageLogEntry.objects.log_action(
            page, "wagtail.publish", user=user, revision=revision, timestamp=when
        )
        page.first_published_at = page.first_published_at or when
        Page.objects.filter(pk=page.pk).update(
            first_published_at=page.first_published_at, last_published_at=when
        )


def remove():
    """Deletes all fake research data. Publish rows outlive their page, so
    they're deleted by hand."""
    parent = Page.objects.filter(depth=2, slug=PARENT_SLUG).first()
    if parent:
        page_ids = list(
            parent.get_descendants(inclusive=True).values_list("id", flat=True)
        )
        PageLogEntry.objects.filter(page_id__in=page_ids).delete()
        Revision.page_revisions.filter(
            object_id__in=[str(page_id) for page_id in page_ids]
        ).delete()
        parent.delete()
    get_user_model().objects.filter(username__startswith=USERNAME_PREFIX).delete()


def create(now):
    """Replaces any earlier fake data with a new set, dated back from now."""
    remove()
    site = _FakeSite()

    # Four months ago: six people join. Five publish their first pages,
    # one only saves a draft, and five drafts are never published.
    for person in range(1, 7):
        site.join(person, _day(now, 4))
    published = [("p1", 1), ("p2", 1), ("p3", 1), ("p4", 2), ("p5", 3), ("p6", 4)]
    for name, person in published + [("p7", 5)]:
        site.publish(name, person, _day(now, 4))
    for name, person in [("d1", 6), ("d2", 1), ("d3", 2), ("d4", 3), ("d5", 4)]:
        site.draft(name, person, _day(now, 4))

    # Three months ago: three join, plus one unverified account that
    # doesn't count. The Peoply sync publishes p8 (no person). Person 1
    # republishes p1: not a first time, not a new page. Person 7 starts p9
    # (published later, so not abandoned) and d6 (abandoned).
    for person in (7, 8, 13):
        site.join(person, _day(now, 3))
    site.join(99, _day(now, 3), verified=False)
    site.publish("p8", None, _day(now, 3))
    site.publish("p1", 1, _day(now, 3))
    site.draft("p9", 7, _day(now, 3))
    site.draft("d6", 7, _day(now, 3))

    # Two months ago: person 6 publishes p8 for the first time themselves.
    # It's their first publish, but p8 was first published by the sync.
    site.publish("p8", 6, _day(now, 2))

    # Last month: five join, person 9 at 23:30 UTC on the last day of the
    # month before (already this month in Oslo). Person 14 never does
    # anything. Five first-time publishers, and person 1 again.
    site.join(9, _late_last_day(now, 2))
    for person in (10, 11, 12, 14):
        site.join(person, _day(now, 1))
    published = [("p9", 7), ("p10", 8), ("p11", 9), ("p12", 10), ("p13", 11)]
    for name, person in published + [("p14", 1)]:
        site.publish(name, person, _day(now, 1))

    # Person 13's two drafts: 31 days old counts as abandoned, 29 not yet.
    site.draft("d7", 13, now - timedelta(days=31))
    site.draft("d8", 13, now - timedelta(days=29))

    return expected_site(now)


def expected_site(now):
    """The site totals create(now) should give: {"YYYY-MM": {column:
    count}}, every column filled in, 0 included."""
    totals = {
        month_of(_day(now, months_back)): dict(zip(SITE_COLUMNS, counts))
        for months_back, counts in EXPECTED_SITE.items()
    }
    abandoned, too_new = now - timedelta(days=31), now - timedelta(days=29)
    months_with_drafts = {month_of(abandoned), month_of(too_new)}
    for month in months_with_drafts:
        totals.setdefault(month, dict.fromkeys(SITE_COLUMNS, 0))
        totals[month]["people_saved_draft"] += 1
    totals[month_of(abandoned)]["drafts_never_published"] += 1
    return totals


def _api_time(moment):
    return moment.astimezone(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _person(number):
    return {"login": f"fake-person-{number}", "id": 1000 + number, "type": "User"}


DEPENDABOT = {"login": "dependabot[bot]", "id": 1, "type": "Bot"}
APP_BOT = {"login": "fake-app[bot]", "id": 2, "type": "User"}  # a bot by name only
SITE_BUG_BODY = "The menu is gone.\n\nFound on page: /nb/info/"
IFI_MESSAGE = "Fix a thing\n\nMade-with: ifi"


class _FakeGitHub:
    def __init__(self):
        self.issues, self.pulls, self.commits = [], [], []

    def issue(self, when, user, labels=(), body="", closed=(None, None)):
        """An issue. closed: when and why it was closed."""
        closed_at, reason = closed
        self.issues.append(
            {
                "user": user,
                "created_at": _api_time(when),
                "labels": [{"name": label} for label in labels],
                "body": body,
                "closed_at": closed_at and _api_time(closed_at),
                "state_reason": reason,
            }
        )

    def pull(self, opened, user, merged=None):
        """A pull request. GitHub lists it among the issues too."""
        pull = {
            "user": user,
            "created_at": _api_time(opened),
            "merged_at": merged and _api_time(merged),
        }
        self.pulls.append(pull)
        self.issues.append({**pull, "labels": [], "pull_request": {}})

    def commit(self, when, message, email, user=None):
        """A commit. user=None: an email GitHub doesn't know."""
        self.commits.append(
            {
                "commit": {
                    "message": message,
                    "author": {"date": _api_time(when), "email": email},
                },
                "author": user,
            }
        )


def github(now):
    """Made-up GitHub data dated back from now, shaped like github_api's
    answers: {"issues": [...], "pulls": [...], "commits": [...]}."""
    fake = _FakeGitHub()

    # Four months ago: five bug reports through the site's "Report a bug"
    # link, one old issue without labels, and a bot's issue (doesn't
    # count). Five people get their first pull request merged; two bots'
    # don't count. Five ifi commits by three people, and a plain commit.
    when = _day(now, 4)
    for number in range(1, 6):
        fake.issue(when, _person(number), ["bug"], body=SITE_BUG_BODY)
        fake.pull(when, _person(number), merged=when)
    fake.issue(when, _person(1))
    fake.issue(when, DEPENDABOT, ["bug"])
    fake.pull(when, DEPENDABOT, merged=when)
    fake.pull(when, APP_BOT, merged=when)
    for number in (1, 1, 2, 2, 3):
        fake.commit(when, IFI_MESSAGE, f"person{number}@example.com", _person(number))
    fake.commit(when, "Plain commit", "person4@example.com", _person(4))

    # Three months ago: five feature requests, one docs issue (labelled
    # docs and task: counts as docs only), and six good first issues
    # (labelled task). Five are done next month, one is closed as not
    # planned (doesn't count). Person 1 opens a pull request merged next
    # month (not their first), person 6 one that's never merged.
    when, next_month = _day(now, 3), _day(now, 2)
    for number in range(6, 11):
        fake.issue(when, _person(number), ["feature"])
    fake.issue(when, _person(1), ["docs", "task"])
    for reason in ["completed"] * 5 + ["not_planned"]:
        good_first = ["good first issue", "task"]
        fake.issue(when, _person(1), good_first, closed=(next_month, reason))
    fake.pull(when, _person(1), merged=next_month)
    fake.pull(when, _person(6))

    # Two months ago, besides the above: an ifi commit from an email GitHub
    # doesn't know.
    fake.commit(next_month, IFI_MESSAGE, "nobody@example.com")

    # Last month: a bug report made 23:30 UTC on the last day of the month
    # before (already this month in Oslo), and five docs issues. Persons
    # 6-10 get their first pull request merged (person 6's first one never
    # was), and person 1 another. Six ifi commits by five people.
    fake.issue(_late_last_day(now, 2), _person(2), ["bug"])
    when = _day(now, 1)
    for number in range(3, 8):
        fake.issue(when, _person(number), ["docs", "task"])
    for number in (6, 7, 8, 9, 10, 1):
        fake.pull(when, _person(number), merged=when)
    for number in (4, 4, 5, 6, 7, 8):
        fake.commit(when, IFI_MESSAGE, f"person{number}@example.com", _person(number))

    return {"issues": fake.issues, "pulls": fake.pulls, "commits": fake.commits}


def expected_github(now):
    """The GitHub totals github(now) should give, like expected_site()."""
    return {
        month_of(_day(now, months_back)): dict(zip(GITHUB_COLUMNS, counts))
        for months_back, counts in EXPECTED_GITHUB.items()
    }
