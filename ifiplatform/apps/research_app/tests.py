# pylint: disable=C0114,C0115,C0116
from datetime import datetime, timezone as dt_timezone
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, TestCase, override_settings
from wagtail.models import Page, PageLogEntry, Revision

from research_app import fake_data
from research_app.totals import (
    GITHUB_COLUMNS,
    SITE_COLUMNS,
    github_totals,
    last_complete_month,
    month_of,
    months_between,
    show,
    site_totals,
)

User = get_user_model()


def _at(text):
    return datetime.fromisoformat(text).replace(tzinfo=dt_timezone.utc)


class HelperTests(SimpleTestCase):
    def test_small_numbers_are_hidden(self):
        self.assertEqual(show(0), "0")
        self.assertEqual(show(1), "<5")
        self.assertEqual(show(4), "<5")
        self.assertEqual(show(5), "5")

    def test_months_between_crosses_a_year(self):
        self.assertEqual(
            months_between("2026-11", "2027-02"),
            ["2026-11", "2026-12", "2027-01", "2027-02"],
        )

    def test_last_complete_month(self):
        self.assertEqual(last_complete_month(_at("2026-11-15 12:00")), "2026-10")
        self.assertEqual(last_complete_month(_at("2027-01-01 12:00")), "2026-12")

    def test_months_are_in_oslo_time(self):
        # 23:30 UTC on 31 October is 00:30 on 1 November in Oslo.
        self.assertEqual(month_of(_at("2026-10-31 23:30")), "2026-11")


def _user(login, user_id, bot=False):
    return {"login": login, "id": user_id, "type": "Bot" if bot else "User"}


class GithubTotalsTests(SimpleTestCase):
    def test_issues(self):
        issues = [
            {
                "user": _user("ada", 1),
                "created_at": "2026-11-03T10:00:00Z",
                "labels": [{"name": "bug"}],
                "body": "Related\nFound on page: /nb/info/",
            },
            {
                "user": _user("ada", 1),
                "created_at": "2026-11-04T10:00:00Z",
                "labels": [{"name": "docs"}, {"name": "task"}],
                "body": None,
            },
            {
                "user": _user("bob", 2),
                "created_at": "2026-10-01T10:00:00Z",
                "closed_at": "2026-11-20T10:00:00Z",
                "state_reason": "completed",
                "labels": [{"name": "good first issue"}, {"name": "feature"}],
                "body": "",
            },
            {  # a pull request in the issues list: not an issue
                "user": _user("ada", 1),
                "created_at": "2026-11-05T10:00:00Z",
                "labels": [],
                "pull_request": {},
            },
            {  # bots don't count
                "user": _user("dependabot[bot]", 3, bot=True),
                "created_at": "2026-11-06T10:00:00Z",
                "labels": [{"name": "bug"}],
            },
        ]
        totals = github_totals(issues, [], [])
        november = totals["2026-11"]
        self.assertEqual(november["issues_opened"], 2)
        self.assertEqual(november["bug_reports"], 1)
        self.assertEqual(november["docs_issues"], 1)
        self.assertNotIn("task_issues", november)
        self.assertEqual(november["issues_from_site"], 1)
        self.assertEqual(november["good_first_issues_closed"], 1)
        self.assertEqual(totals["2026-10"]["feature_requests"], 1)

    def test_pull_requests(self):
        pulls = [
            {
                "user": _user("ada", 1),
                "created_at": "2026-10-01T10:00:00Z",
                "merged_at": "2026-10-02T10:00:00Z",
            },
            {
                "user": _user("ada", 1),
                "created_at": "2026-11-01T10:00:00Z",
                "merged_at": "2026-11-02T10:00:00Z",
            },
            {
                "user": _user("bob", 2),
                "created_at": "2026-11-03T10:00:00Z",
                "merged_at": None,
            },
            {
                "user": _user("github-actions[bot]", 3),
                "created_at": "2026-11-04T10:00:00Z",
                "merged_at": "2026-11-04T11:00:00Z",
            },
        ]
        totals = github_totals([], pulls, [])
        self.assertEqual(totals["2026-11"]["prs_opened"], 2)
        self.assertEqual(totals["2026-11"]["prs_merged"], 1)
        self.assertEqual(totals["2026-11"]["people_opened_pr"], 2)
        # ada's first merge was in October, so November has no first-timers.
        self.assertEqual(totals["2026-10"]["first_time_pr_authors_merged"], 1)
        self.assertNotIn("first_time_pr_authors_merged", totals["2026-11"])

    def test_ifi_commits(self):
        def commit(message, email, author=None):
            return {
                "commit": {
                    "message": message,
                    "author": {"date": "2026-11-10T10:00:00Z", "email": email},
                },
                "author": author,
            }

        commits = [
            commit("Fix menu\n\nMade-with: ifi", "ada@example.com", _user("ada", 1)),
            commit("Fix footer\n\nMade-with: ifi", "ada@example.com", _user("ada", 1)),
            commit("Add test\n\nMade-with: ifi", "nobody@example.com"),
            commit("Plain commit", "bob@example.com", _user("bob", 2)),
        ]
        totals = github_totals([], [], commits)
        self.assertEqual(totals["2026-11"]["ifi_commits"], 3)
        self.assertEqual(totals["2026-11"]["people_using_ifi"], 2)


class SiteTotalsTests(TestCase):
    def setUp(self):
        self.ada = User.objects.create_user(username="ada", password="pw")
        self.bob = User.objects.create_user(username="bob", password="pw")
        User.objects.filter(pk=self.ada.pk).update(date_joined=_at("2026-10-05 12:00"))
        User.objects.filter(pk=self.bob.pk).update(date_joined=_at("2026-11-05 12:00"))
        User.objects.create_user(username="unverified", password="pw", is_active=False)
        self.root = Page.get_first_root_node()

    def _page(self, slug, live=False):
        page = Page(title=slug, slug=slug, live=live)
        self.root.add_child(instance=page)
        return page

    def _publish(self, page, user, when):
        page.save_revision(user=user).publish(user=user, skip_permission_checks=True)
        PageLogEntry.objects.filter(page=page, action="wagtail.publish").update(
            timestamp=when
        )

    def test_accounts_and_publishing(self):
        first = self._page("first")
        self._publish(first, self.ada, _at("2026-10-10 12:00"))
        second = self._page("second")
        self._publish(second, self.ada, _at("2026-11-10 12:00"))
        self._publish(second, self.bob, _at("2026-11-11 12:00"))
        synced = self._page("synced")  # the Peoply sync publishes with no user
        self._publish(synced, None, _at("2026-11-12 12:00"))

        totals = site_totals(_at("2026-12-15 12:00"))
        self.assertEqual(totals["2026-10"]["new_accounts"], 1)
        self.assertEqual(totals["2026-11"]["new_accounts"], 1)  # not "unverified"
        self.assertEqual(totals["2026-10"]["first_time_publishers"], 1)
        self.assertEqual(totals["2026-11"]["first_time_publishers"], 1)
        self.assertEqual(totals["2026-11"]["people_published"], 2)
        self.assertEqual(totals["2026-10"]["pages_first_published"], 1)
        self.assertEqual(totals["2026-11"]["pages_first_published"], 1)

    def test_drafts_never_published(self):
        old_draft = self._page("old-draft")
        old_draft.save_revision(user=self.ada)
        new_draft = self._page("new-draft")
        new_draft.save_revision(user=self.bob)
        Revision.page_revisions.filter(object_id=str(old_draft.pk)).update(
            created_at=_at("2026-10-01 12:00")
        )
        Revision.page_revisions.filter(object_id=str(new_draft.pk)).update(
            created_at=_at("2026-11-25 12:00")
        )

        totals = site_totals(_at("2026-12-01 12:00"))
        self.assertEqual(totals["2026-10"]["drafts_never_published"], 1)
        # Under 30 days old: it may still be published.
        self.assertNotIn("drafts_never_published", totals["2026-11"])
        self.assertEqual(totals["2026-11"]["people_saved_draft"], 1)


class FakeDataTests(TestCase):
    # The second date is just after midnight on 1 March in Oslo, still
    # February in UTC, with a short month before it.
    NOWS = (_at("2026-11-15 12:00"), _at("2027-02-28 23:30"))

    def _assert_totals(self, totals, expected, columns, now):
        for month in sorted(expected.keys() | totals.keys()):
            with self.subTest(now=now, month=month):
                found = totals.get(month, {})
                self.assertEqual(
                    {column: found.get(column, 0) for column in columns},
                    expected.get(month),
                )

    def test_site_totals_are_what_the_fake_data_expects(self):
        for now in self.NOWS:
            expected = fake_data.create(now)
            self._assert_totals(site_totals(now), expected, SITE_COLUMNS, now)

    def test_github_totals_are_what_the_fake_data_expects(self):
        for now in self.NOWS:
            totals = github_totals(**fake_data.github(now))
            expected = fake_data.expected_github(now)
            self._assert_totals(totals, expected, GITHUB_COLUMNS, now)

    def test_remove_leaves_nothing(self):
        now = _at("2026-11-15 12:00")
        fake_data.create(now)
        fake_data.remove()
        self.assertEqual(site_totals(now), {})
        self.assertFalse(
            User.objects.filter(username__startswith=fake_data.USERNAME_PREFIX).exists()
        )


class CommandTests(TestCase):
    @override_settings(DEBUG=True)
    def test_seed_and_totals_give_the_same_csv(self):
        with TemporaryDirectory() as folder:
            fake_github = str(Path(folder) / "fake_github.json")
            for github in (["--no-github"], ["--github-file", fake_github]):
                with self.subTest(github=github[0]):
                    expected = Path(folder) / "expected.csv"
                    totals = Path(folder) / "totals.csv"
                    seed_github = github if github[0] == "--github-file" else []
                    call_command(
                        "seed_research_data",
                        "--output",
                        expected,
                        *seed_github,
                        stdout=StringIO(),
                    )
                    call_command(
                        "research_totals",
                        *github,
                        "--output",
                        totals,
                        stdout=StringIO(),
                        stderr=StringIO(),
                    )
                    self.assertEqual(totals.read_text(), expected.read_text())
                    self.assertEqual(
                        "issues_opened" in totals.read_text(), bool(seed_github)
                    )

    def test_bad_github_file(self):
        with self.assertRaises(CommandError):
            call_command("research_totals", "--github-file", "no-such-file.json")

    def test_seed_needs_debug(self):
        with self.assertRaises(CommandError):
            call_command("seed_research_data", stdout=StringIO())

    def test_says_when_this_month_is_left_out(self):
        User.objects.create_user(username="ada", password="pw")
        err = StringIO()
        call_command("research_totals", "--no-github", stdout=StringIO(), stderr=err)
        self.assertIn("--until", err.getvalue())

    def test_csv_without_github(self):
        User.objects.create_user(username="ada", password="pw")
        out = StringIO()
        call_command(
            "research_totals",
            "--no-github",
            "--since",
            "2026-01",
            "--until",
            "2026-02",
            stdout=out,
        )
        lines = out.getvalue().splitlines()
        self.assertEqual(lines[0].split(",")[0], "month")
        self.assertNotIn("issues_opened", lines[0])
        self.assertEqual(
            [line.split(",")[0] for line in lines[1:]], ["2026-01", "2026-02"]
        )
        self.assertNotIn("ada", out.getvalue())

    def test_github_is_used_unless_turned_off(self):
        out = StringIO()
        with mock.patch(
            "research_app.management.commands.research_totals.github_api"
        ) as api:
            api.get_issues.return_value = []
            api.get_pulls.return_value = []
            api.get_commits.return_value = []
            call_command(
                "research_totals",
                "--since",
                "2026-01",
                "--until",
                "2026-01",
                stdout=out,
            )
        self.assertIn("issues_opened", out.getvalue().splitlines()[0])

    def test_bad_month(self):
        with self.assertRaises(CommandError):
            call_command("research_totals", "--no-github", "--since", "2026-13")

    def test_since_after_until(self):
        with self.assertRaises(CommandError):
            call_command(
                "research_totals",
                "--no-github",
                "--since",
                "2026-05",
                "--until",
                "2026-04",
            )
