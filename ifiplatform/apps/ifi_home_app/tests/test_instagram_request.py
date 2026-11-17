# pylint: disable=C0114,C0115,C0116
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone, translation

from ifi_home_app.models import InstagramAccount, InstagramAccountRequest, InstagramPost
from ifi_home_app.models.instagram_request import (
    APPROVED,
    DECLINED,
    PENDING,
    REQUESTS_PER_HOUR,
    delete_old_requests,
)

STEP_TWO = {
    "step": "request",
    "ifi_related": "True",
    "username": "@IfiTestGroup",
    "kind": "union",
    "reason": "The board game group at IFI.",
    "contact_email": "",
    "website": "",
}


def _request(**kwargs):
    kwargs.setdefault("username", "ifitestgroup")
    kwargs.setdefault("reason", "The board game group at IFI.")
    return InstagramAccountRequest.objects.create(**kwargs)


class RequestPageTests(TestCase):
    def post(self, data, language="en"):
        with translation.override(language):
            return self.client.post(reverse("instagram_request"), data)

    def test_step_one_explains_what_instagram_needs(self):
        response = self.post({"step": "check", "is_public": "on", "ifi_related": "on"})
        html = response.content.decode()
        self.assertIn("Instagram only lets us show public business or creator", html)
        self.assertNotIn("Send request", html)

    def test_step_two_asks_why_when_not_ifi_related(self):
        html = self.post(
            {"step": "check", "is_public": "on", "is_professional": "on"}
        ).content.decode()
        self.assertIn("Why should it be shown anyway?", html)
        self.assertIn('name="ifi_related" value="False"', html)

    def test_step_two_asks_how_when_ifi_related(self):
        html = self.post(
            {
                "step": "check",
                "is_public": "on",
                "is_professional": "on",
                "ifi_related": "on",
            }
        ).content.decode()
        self.assertIn("How is it related to IFI?", html)

    def test_back_keeps_the_ticks(self):
        html = self.post({**STEP_TWO, "step": "back"}).content.decode()
        self.assertIn("Can the account be shown?", html)
        self.assertEqual(html.count("checked"), 3)

    def test_sends_a_waiting_request(self):
        response = self.post(STEP_TWO)
        self.assertRedirects(
            response, "/en/instagram/request/?sent=1", fetch_redirect_response=False
        )
        request = InstagramAccountRequest.objects.get()
        self.assertEqual(request.username, "ifitestgroup")
        self.assertEqual(request.status, PENDING)
        self.assertEqual(request.language, "en")
        self.assertTrue(request.ifi_related)

    def test_takes_a_pasted_instagram_address(self):
        self.post(
            {**STEP_TWO, "username": "https://www.instagram.com/IfiTestGroup/?hl=nb"}
        )
        self.assertEqual(InstagramAccountRequest.objects.get().username, "ifitestgroup")

    def test_rejects_listed_and_already_requested_accounts(self):
        html = self.post({**STEP_TWO, "username": "ifinavet"}).content.decode()
        self.assertIn("@ifinavet is already in Ifi Instagram.", html)
        _request(username="waiting_one")
        html = self.post({**STEP_TWO, "username": "waiting_one"}).content.decode()
        self.assertIn("@waiting_one has already been requested.", html)
        self.assertEqual(InstagramAccountRequest.objects.count(), 1)

    def test_rejects_what_cannot_be_a_username(self):
        html = self.post({**STEP_TWO, "username": "not a name!"}).content.decode()
        self.assertIn("Use the name from the account&#x27;s Instagram address", html)

    def test_honeypot_creates_nothing(self):
        response = self.post({**STEP_TWO, "website": "http://spam.example"})
        self.assertRedirects(
            response, "/en/instagram/request/?sent=1", fetch_redirect_response=False
        )
        self.assertFalse(InstagramAccountRequest.objects.exists())

    def test_hourly_limit_for_the_whole_site(self):
        for i in range(REQUESTS_PER_HOUR):
            _request(username=f"account{i}")
        html = self.post(STEP_TWO).content.decode()
        self.assertIn("lot of requests in the last hour", html)
        self.assertEqual(InstagramAccountRequest.objects.count(), REQUESTS_PER_HOUR)

    def test_norwegian_page(self):
        with translation.override("nb"):
            html = self.client.get(reverse("instagram_request")).content.decode()
        self.assertIn("Kan kontoen vises?", html)
        self.assertIn("Den er en bedrifts- eller innholdsskaperkonto", html)

    def test_thank_you(self):
        with translation.override("en"):
            html = self.client.get(reverse("instagram_request") + "?sent=1").content
        self.assertIn(b"Thanks!", html)

    def test_feed_links_to_the_page(self):
        account = InstagramAccount.objects.get(username="ifinavet")
        post = InstagramPost(
            account=account,
            permalink="https://www.instagram.com/p/X/",
            posted_at=timezone.now(),
        )
        post.image.name = "instagram/posts/x.jpg"
        with translation.override("en"):
            html = render_to_string(
                "home/partials/instagram/instagram.html", {"instagram_posts": [post]}
            )
        self.assertIn(
            "Run an IFI-related account? "
            '<a href="/en/instagram/request/">Suggest an account to show here &rarr;</a>',
            html,
        )
        self.assertIn(
            '<button class="home-instagram-view-all" type="button" hidden>Show more</button>',
            html,
        )


class DecisionTests(TestCase):
    def test_approving_adds_the_account_and_tells_the_requester(self):
        request = _request(kind="humour", contact_email="a@example.com", language="nb")
        request.status = APPROVED
        request.save()
        account = InstagramAccount.objects.get(username="ifitestgroup")
        self.assertTrue(account.is_active)
        self.assertEqual(account.kind, "humour")
        self.assertIsNotNone(request.decided_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["a@example.com"])
        self.assertIn("@ifitestgroup er nå med i Ifi Instagram", mail.outbox[0].body)

    def test_approving_turns_a_switched_off_account_back_on(self):
        InstagramAccount.objects.filter(username="ifinavet").update(
            is_active=False, sync_paused=True, failed_runs=3
        )
        request = _request(username="ifinavet")
        request.status = APPROVED
        request.save()
        account = InstagramAccount.objects.get(username="ifinavet")
        self.assertTrue(account.is_active)
        self.assertFalse(account.sync_paused)
        self.assertEqual(account.failed_runs, 0)

    def test_declining_tells_the_requester_with_the_answer(self):
        request = _request(contact_email="a@example.com", language="en")
        request.status = DECLINED
        request.answer = "It's a personal account."
        request.save()
        self.assertFalse(
            InstagramAccount.objects.filter(username="ifitestgroup").exists()
        )
        self.assertIn("won't be shown", mail.outbox[0].body)
        self.assertIn("It's a personal account.", mail.outbox[0].body)

    def test_only_the_first_decision_counts(self):
        request = _request(contact_email="a@example.com")
        request.status = DECLINED
        request.save()
        request.status = APPROVED
        request.save()
        self.assertFalse(
            InstagramAccount.objects.filter(username="ifitestgroup").exists()
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_no_email_without_an_address(self):
        request = _request()
        request.status = APPROVED
        request.save()
        self.assertEqual(mail.outbox, [])

    def test_decided_requests_are_deleted_after_six_months(self):
        old = _request(username="old_one", status=DECLINED)
        recent = _request(username="recent_one", status=DECLINED)
        waiting = _request(username="waiting_one")
        InstagramAccountRequest.objects.filter(pk=old.pk).update(
            decided_at=timezone.now() - timedelta(days=181)
        )
        InstagramAccountRequest.objects.filter(pk=recent.pk).update(
            decided_at=timezone.now() - timedelta(days=10)
        )
        self.assertEqual(delete_old_requests(), 1)
        self.assertEqual(
            set(InstagramAccountRequest.objects.values_list("pk", flat=True)),
            {recent.pk, waiting.pk},
        )


class DashboardTests(TestCase):
    def setUp(self):
        # Admin requests switch the active language; put it back afterwards.
        self.enterContext(translation.override("en"))

    def test_admins_see_how_many_requests_wait(self):
        admin = get_user_model().objects.create_superuser(
            "admin", "x@example.com", "pw"
        )
        self.client.force_login(admin)
        _request()
        html = self.client.get(reverse("wagtailadmin_home")).content.decode()
        self.assertIn("1 Instagram account request waiting", html)
        self.assertIn("instagramaccountrequest/?status=pending", html)

    def test_admins_see_paused_accounts(self):
        admin = get_user_model().objects.create_superuser(
            "admin", "x@example.com", "pw"
        )
        self.client.force_login(admin)
        InstagramAccount.objects.filter(username="mapsuio").update(sync_paused=True)
        html = self.client.get(reverse("wagtailadmin_home")).content.decode()
        self.assertIn("1 Instagram account paused", html)
        self.assertIn("@mapsuio", html)

    def test_admins_can_open_and_answer_a_request_but_not_add_one(self):
        admin = get_user_model().objects.create_superuser(
            "admin", "x@example.com", "pw"
        )
        self.client.force_login(admin)
        request = _request()
        prefix = "wagtailsnippets_ifi_home_app_instagramaccountrequest"
        self.assertEqual(self.client.get(reverse(f"{prefix}:list")).status_code, 200)
        edit = self.client.get(reverse(f"{prefix}:edit", args=[request.pk]))
        self.assertEqual(edit.status_code, 200)
        self.assertContains(edit, "The board game group at IFI.")
        self.assertNotEqual(self.client.get(reverse(f"{prefix}:add")).status_code, 200)
