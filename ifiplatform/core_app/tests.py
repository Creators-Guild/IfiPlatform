# pylint: disable=C0114,C0115,C0116
import re
import time

from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, RequestFactory, TestCase, TransactionTestCase, tag
from django.urls import reverse

from core_app.deploy_notice import deploy_notice


class DeployNoticeTests(TestCase):
    """Covers the read side (deploy_notice context processor) of the
    site-wide deploy countdown banner -- see announce_deploy (the write
    side) and templates/partials/deploy_notice.html (the render side, one
    include in global_base.html covering every page)."""

    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()

    def test_no_active_announcement_is_none(self):
        request = self.factory.get("/")
        self.assertIsNone(deploy_notice(request)["deploy_notice_target"])

    def test_announce_deploy_sets_the_target_the_processor_reads(self):
        before = int(time.time())
        call_command("announce_deploy", "--minutes", "10")
        after = int(time.time())

        request = self.factory.get("/")
        target = deploy_notice(request)["deploy_notice_target"]

        self.assertIsNotNone(target)
        # target should be ~10 minutes from whenever the command actually
        # ran, not off by an unrelated amount.
        self.assertGreaterEqual(target, before + 10 * 60)
        self.assertLessEqual(target, after + 10 * 60)

    def test_clear_removes_an_active_announcement(self):
        call_command("announce_deploy", "--minutes", "10")
        call_command("announce_deploy", "--clear")

        request = self.factory.get("/")
        self.assertIsNone(deploy_notice(request)["deploy_notice_target"])

    def test_clear_is_a_safe_no_op_with_nothing_announced(self):
        call_command("announce_deploy", "--clear")

        request = self.factory.get("/")
        self.assertIsNone(deploy_notice(request)["deploy_notice_target"])


class DeployNoticeStatusViewTests(TestCase):
    """The endpoint deploy_notice.js polls from already-open tabs (see that
    file's own poll()) -- what makes an announcement appear/disappear
    without the visitor reloading or navigating anywhere."""

    def setUp(self):
        cache.clear()

    def test_no_active_announcement_returns_null_target(self):
        response = self.client.get(reverse("deploy_notice_status"))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["target"])

    def test_active_announcement_returns_the_target(self):
        call_command("announce_deploy", "--minutes", "10")
        response = self.client.get(reverse("deploy_notice_status"))
        self.assertIsNotNone(response.json()["target"])

    def test_cleared_announcement_returns_null_again(self):
        call_command("announce_deploy", "--minutes", "10")
        call_command("announce_deploy", "--clear")
        response = self.client.get(reverse("deploy_notice_status"))
        self.assertIsNone(response.json()["target"])


@tag("slow")
class SiteCrawlTests(TransactionTestCase):
    """Crawls the whole public site starting from each locale's homepage,
    following every internal link it finds, and fails if any of them is
    broken. Exists because of a real incident: a stale Wagtail
    site-root-paths cache silently turned every {% pageurl %} link on the
    site into a literal href="None" -- nothing caught it until someone
    clicked around by hand. See clear_cache's own docstring for the root
    cause.

    Only follows same-origin links, skipping static/media/admin and
    anything that isn't a path (external links, mailto:, "#", ...).
    href="" is a deliberate placeholder convention on this site (sections
    not built yet -- see APPS_UNDER_DEVELOPMENT), so it's not treated as
    broken; a literal href="None" always is, since that can only come from
    a template tag that failed to resolve a real page's URL.

    TransactionTestCase, not TestCase: wagtail_localize defers each
    translated page's actual publish (the flip to live=True) to
    transaction.on_commit() (see create_or_update_translation in
    wagtail_localize/models.py). Plain TestCase wraps every test in a
    transaction that gets rolled back, never committed, so those on_commit
    callbacks would never fire and every translated page would come out
    live=False here -- a test-harness artifact, not a real bug. Confirmed
    by reproducing it against a real Postgres database outside the test
    runner, where seed_dev_data behaves correctly."""

    HREF_RE = re.compile(r'href="([^"]*)"')
    EXCLUDED_PREFIXES = ("/static/", "/media/", "/admin/", "/wagtail-admin/")
    # Safety net against a runaway crawl (e.g. a link cycle), not a real
    # expectation -- seed_dev_data's tree is intentionally small.
    MAX_PAGES = 300

    def setUp(self):
        # --force: seed_dev_data refuses to run with DEBUG off, which the
        # test runner always forces regardless of .env -- safe here since
        # this only ever touches the throwaway test database.
        call_command("seed_dev_data", "--force")

    def test_crawl_finds_no_broken_links(self):
        client = Client()
        # href -> page it was first discovered on, for actionable failures.
        to_visit = {"/en/": "(start)", "/nb/": "(start)"}
        visited = set()
        broken = []

        while to_visit and len(visited) < self.MAX_PAGES:
            url, source = to_visit.popitem()
            if url in visited:
                continue
            visited.add(url)

            try:
                response = client.get(url, follow=True)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                # A render/view crash is exactly the kind of thing this test
                # exists to catch -- record it and keep crawling instead of
                # letting one broken page hide every other result.
                broken.append(
                    f"{url!r} (linked from {source}) -> "
                    f"{exc.__class__.__name__}: {exc}"
                )
                continue

            if response.status_code != 200:
                broken.append(
                    f"{url!r} (linked from {source}) -> HTTP {response.status_code}"
                )
                continue

            html = response.content.decode("utf-8", errors="replace")
            for href in self.HREF_RE.findall(html):
                if href == "None":
                    broken.append(
                        f'href="None" found on {url!r} '
                        "(a page-link tag resolved to no URL)"
                    )
                    continue
                if not href.startswith("/") or href.startswith(self.EXCLUDED_PREFIXES):
                    continue
                if href not in visited and href not in to_visit:
                    to_visit[href] = url

        self.assertLess(
            len(visited),
            self.MAX_PAGES,
            "Crawl hit MAX_PAGES -- either the site legitimately grew this "
            "large (raise the cap) or something is generating a link cycle.",
        )

        if broken:
            details = "\n".join(f"  - {b}" for b in broken)
            self.fail(f"Found {len(broken)} broken link(s):\n{details}")
