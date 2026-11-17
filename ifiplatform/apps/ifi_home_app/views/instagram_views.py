"""The public "Suggest an account to show here" page of the homepage's Ifi Instagram feed:
step 1 checks what Instagram needs, step 2 sends the request, which admins
answer in the "Instagram account requests" snippet. Plain form posts, so it
works without JavaScript.

Design rationale: docs/claude_context/home_instagram.md"""

import subprocess
import sys

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _

from ..forms import InstagramCheckForm, InstagramRequestForm
from ..models.instagram import InstagramSyncLog, InstagramSyncState
from ..models.instagram_request import too_many_requests

TEMPLATE = "home/instagram_request.html"


def instagram_request(request):
    """Shows step 1 ("check"), step 2 ("request") or the thank-you ("sent")."""
    if request.GET.get("sent"):
        return render(request, TEMPLATE, {"step": "sent"})
    step = request.POST.get("step") if request.method == "POST" else None
    if step == "check":
        return _check(request)
    if step == "request":
        return _send(request)
    return _start(request, back=step == "back")


def _start(request, back):
    """Step 1. "← Back" from step 2 shows it again with what was ticked."""
    form = InstagramCheckForm(
        initial={
            "is_public": back,
            "is_professional": back,
            "ifi_related": request.POST.get("ifi_related") != "False",
        }
    )
    return render(request, TEMPLATE, {"step": "check", "form": form})


def _check(request):
    """Step 1 sent: on to step 2 if both required boxes are ticked."""
    form = InstagramCheckForm(request.POST)
    if not form.is_valid():
        return render(request, TEMPLATE, {"step": "check", "form": form})
    form = InstagramRequestForm(
        initial={"ifi_related": form.cleaned_data["ifi_related"]}
    )
    return render(request, TEMPLATE, {"step": "request", "form": form})


def _send(request):
    """Step 2 sent: save the request, then show the thank-you."""
    sent_url = f"{reverse('instagram_request')}?sent=1"
    form = InstagramRequestForm(request.POST)
    if form.data.get("website"):
        return redirect(sent_url)  # a bot filled in the honeypot: pretend it worked
    if too_many_requests():
        form.add_error(
            None,
            _("We've had a lot of requests in the last hour. Please try again later."),
        )
    elif form.is_valid():
        account_request = form.save(commit=False)
        account_request.language = translation.get_language() or "nb"
        account_request.save()
        return redirect(sent_url)
    return render(request, TEMPLATE, {"step": "request", "form": form})


@require_POST
def force_sync_instagram(request):
    """Staff-only "Sync Instagram now" (home/partials/instagram/
    sync_button.html), like event_views.force_sync_peoply_events. A sync
    takes from ~30 s to minutes (Meta calls and media downloads), longer
    than a request may run, so it starts sync_instagram_posts as its own
    process and comes straight back; the command's run lock
    (InstagramSyncState.claim_run) turns a second start into a no-op.
    Every click is logged (InstagramSyncLog)."""
    if not request.user.is_staff:
        raise PermissionDenied
    InstagramSyncLog.objects.create(user=request.user)
    if InstagramSyncState.is_running():
        state = "running"
    else:
        # pylint: disable-next=consider-using-with
        subprocess.Popen(
            [
                sys.executable,
                str(settings.BASE_DIR / "manage.py"),
                "sync_instagram_posts",
            ],
            cwd=settings.BASE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        state = "started"
    next_url = request.POST.get("next")
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = "/"
    return redirect(f"{next_url}?instagram_sync={state}#home-instagram-heading")
