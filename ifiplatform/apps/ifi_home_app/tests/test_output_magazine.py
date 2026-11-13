# pylint: disable=C0114,C0115,C0116
import json
from datetime import date, timedelta
from io import StringIO
from unittest.mock import Mock, patch

import requests
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from ifi_home_app.integrations.ifiavis import (
    IfiavisParseError,
    parse_issue_date,
    parse_issues,
)
from ifi_home_app.models import MagazineIssue
from ifi_home_app.wagtail_hooks import MagazineIssueViewSet

CDN = "https://cdn.sanity.io/images/z7zut3cm/production/"


def _card(key, slug, cover, title, date_node):
    return [
        "$",
        "$L12",
        key,
        {
            "href": f"/utgaver/{slug}",
            "className": "group block",
            "children": [
                [
                    "$",
                    "div",
                    None,
                    {
                        "children": [
                            "$",
                            "$L13",
                            None,
                            {
                                "src": f"{CDN}{cover}?rect=46,0,2528,3370&w=900&h=1200&fit=crop",
                                "alt": title,
                            },
                        ]
                    },
                ],
                [
                    "$",
                    "div",
                    None,
                    {
                        "children": [
                            ["$", "div", None, {"children": title}],
                            date_node,
                        ]
                    },
                ],
            ],
        },
    ]


def _date(text):
    return ["$", "div", None, {"className": "text-xs", "children": text}]


def _page(rows):
    """An /utgaver page in Next.js's format: rows of "id:json", pushed in
    two chunks so a row is split across them, like on the real page."""
    payload = "".join(f"{row_id}:{json.dumps(value)}\n" for row_id, value in rows)
    middle = len(payload) // 2
    chunks = [payload[:middle], payload[middle:]]
    scripts = "".join(
        f"<script>self.__next_f.push([1,{json.dumps(chunk)}])</script>" for chunk in chunks
    )
    return f"<html><body><script>self.__next_f.push([0])</script>{scripts}</body></html>"


SAMPLE_PAGE = _page(
    [
        ("0", ["$", "$L1", None, {}]),
        (
            "e",
            [
                "$",
                "section",
                None,
                {
                    "children": [
                        _card("id-15", "output-utg-15", "aaa-623x802.jpg", ">Output utg. 15", _date("april 2026")),
                        _card("id-11", "output-lilla", "bbb-2620x3370.jpg", ">Output utg. 11", "$L14"),
                        "$L15",
                    ]
                },
            ],
        ),
        ("14", _date("mars 2024")),
        ("15", _card("id-14", "rytme", "ccc-2620x3370.jpg", ">Output utg. 14", _date("november 2025"))),
        ("16", 'I["chunks/app.js"]'),
    ]
)


class ParseIssuesTests(SimpleTestCase):
    def test_reads_every_card_newest_first(self):
        issues = parse_issues(SAMPLE_PAGE)
        self.assertEqual([i.sanity_id for i in issues], ["id-15", "id-14", "id-11"])
        first = issues[0]
        self.assertEqual(first.title, ">Output utg. 15")
        self.assertEqual(first.url, "https://www.ifiavis.no/utgaver/output-utg-15")
        self.assertEqual(first.issue_date, date(2026, 4, 1))

    def test_follows_row_references(self):
        by_id = {i.sanity_id: i for i in parse_issues(SAMPLE_PAGE)}
        self.assertEqual(by_id["id-11"].issue_date, date(2024, 3, 1))
        self.assertEqual(by_id["id-14"].url, "https://www.ifiavis.no/utgaver/rytme")

    def test_cover_keeps_crop_but_not_size(self):
        cover = parse_issues(SAMPLE_PAGE)[0].cover_url
        self.assertEqual(cover, CDN + "aaa-623x802.jpg?rect=46,0,2528,3370")

    def test_page_without_issues_raises(self):
        with self.assertRaises(IfiavisParseError):
            parse_issues(_page([("0", ["$", "div", None, {"children": "Hei"}])]))

    def test_card_without_date_raises(self):
        page = _page([("0", _card("id-1", "x", "a.jpg", "X", _date("snart")))])
        with self.assertRaises(IfiavisParseError):
            parse_issues(page)

    def test_parse_issue_date(self):
        self.assertEqual(parse_issue_date("august 2018"), date(2018, 8, 1))
        self.assertEqual(parse_issue_date(" Desember 2030 "), date(2030, 12, 1))
        with self.assertRaises(IfiavisParseError):
            parse_issue_date("august")


def _fake_response(text, status_code=200):
    response = Mock(text=text, status_code=status_code)
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f"{status_code} error")
    return response


def _sync(page=SAMPLE_PAGE, *args):
    out = StringIO()
    with patch(
        "ifi_home_app.integrations.ifiavis.requests.get",
        return_value=_fake_response(page),
    ):
        call_command("sync_output_magazine", *args, stdout=out)
    return out.getvalue()


class SyncOutputMagazineTests(TestCase):
    def test_creates_issues(self):
        _sync()
        self.assertEqual(
            list(MagazineIssue.objects.values_list("sanity_id", flat=True)),
            ["id-15", "id-14", "id-11"],
        )

    def test_updates_synced_fields_but_keeps_hidden(self):
        _sync()
        MagazineIssue.objects.filter(sanity_id="id-15").update(
            title="Old title",
            hidden=True,
            last_seen_at=timezone.now() - timedelta(days=3),
        )
        output = _sync()
        issue = MagazineIssue.objects.get(sanity_id="id-15")
        self.assertEqual(issue.title, ">Output utg. 15")
        self.assertTrue(issue.hidden)
        self.assertGreater(issue.last_seen_at, timezone.now() - timedelta(minutes=1))
        self.assertIn("Changed: >Output utg. 15 (title)", output)

    def test_never_deletes_an_issue_missing_from_the_page(self):
        MagazineIssue.objects.create(
            sanity_id="gone",
            title="Old",
            url="https://www.ifiavis.no/utgaver/old",
            cover_url=CDN + "old.jpg",
            issue_date=date(2017, 1, 1),
            last_seen_at=timezone.now(),
        )
        output = _sync()
        self.assertTrue(MagazineIssue.objects.filter(sanity_id="gone").exists())
        self.assertIn("1 stored issues are no longer listed there", output)

    def test_dry_run_saves_nothing(self):
        output = _sync(SAMPLE_PAGE, "--dry-run")
        self.assertFalse(MagazineIssue.objects.exists())
        self.assertIn("Dry run", output)

    def test_unreadable_page_fails_and_changes_nothing(self):
        _sync()
        with self.assertRaises(CommandError):
            _sync("<html>redesigned</html>")
        self.assertEqual(MagazineIssue.objects.count(), 3)

    def test_http_error_fails(self):
        with patch(
            "ifi_home_app.integrations.ifiavis.requests.get",
            return_value=_fake_response("", status_code=503),
        ):
            with self.assertRaises(CommandError):
                call_command("sync_output_magazine", stdout=StringIO())


class MagazineIssueAdminTests(TestCase):
    def test_nobody_can_add_or_delete_but_admins_can_hide(self):
        admin = get_user_model().objects.create_superuser("admin", "a@example.com", "pw")
        policy = MagazineIssueViewSet().permission_policy
        self.assertFalse(policy.user_has_permission(admin, "add"))
        self.assertFalse(policy.user_has_permission(admin, "delete"))
        self.assertTrue(policy.user_has_permission(admin, "change"))
        self.assertFalse(policy.users_with_any_permission(["add", "delete"]).exists())


class MagazineBoxTemplateTests(TestCase):
    def _issue(self, **kwargs):
        defaults = {
            "sanity_id": "id-15",
            "title": ">Output utg. 15",
            "url": "https://www.ifiavis.no/utgaver/output-utg-15",
            "cover_url": CDN + "aaa.jpg?rect=11,0,602,802",
            "issue_date": date(2026, 4, 1),
            "last_seen_at": timezone.now(),
        }
        defaults.update(kwargs)
        return MagazineIssue.objects.create(**defaults)

    def test_cover_src_adds_size_after_existing_query(self):
        issue = self._issue()
        self.assertEqual(
            issue.cover_src(400),
            CDN + "aaa.jpg?rect=11,0,602,802&w=400&h=533&fit=crop&auto=format",
        )

    def test_renders_each_issue_with_its_link(self):
        self._issue()
        self._issue(sanity_id="id-14", title=">Output utg. 14", url="https://www.ifiavis.no/utgaver/rytme")
        html = render_to_string(
            "home/partials/magazinebox/magazinebox.html",
            {"magazine_issues": list(MagazineIssue.objects.all())},
        )
        self.assertIn('href="https://www.ifiavis.no/utgaver/rytme"', html)
        self.assertIn('href="https://www.ifiavis.no/utgaver"', html)
        self.assertEqual(html.count('class="home-magazinebox-slide"'), 2)
        self.assertEqual(html.count('loading="lazy"'), 1)

    def test_renders_nothing_without_issues(self):
        html = render_to_string("home/partials/magazinebox/magazinebox.html", {"magazine_issues": []})
        self.assertEqual(html.strip(), "")
