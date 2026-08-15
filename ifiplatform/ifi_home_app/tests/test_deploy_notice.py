# pylint: disable=C0114,C0115,C0116
import time

from django.core.cache import cache
from django.core.management import call_command
from django.test import RequestFactory, TestCase
from django.urls import reverse

from ifi_home_app.infra.deploy_notice import deploy_notice


class DeployNoticeTests(TestCase):
    """Covers the read side (deploy_notice context processor) of the
    site-wide deploy countdown banner -- see announce_deploy (the write
    side) and templates/partials/deploy_notice.html (the render side, one
    include in ifi_base.html covering every page)."""

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
