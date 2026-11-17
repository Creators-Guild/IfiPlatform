"""The public "Suggest an account to show here" page of the homepage's Ifi Instagram feed:
step 1 checks what Instagram needs, step 2 sends the request, which admins
answer in the "Instagram account requests" snippet. Plain form posts, so it
works without JavaScript.

Design rationale: docs/claude_context/home_instagram.md"""

from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _

from ..forms import InstagramCheckForm, InstagramRequestForm
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
