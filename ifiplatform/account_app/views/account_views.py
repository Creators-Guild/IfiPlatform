"""Views for account settings and user profile management."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse

from account_app.forms import ProfileForm
from account_app.models import Profile

_EMAIL_CHANGE_SALT = "account_app.email_change"
_EMAIL_CHANGE_MAX_AGE = 60 * 60 * 24 * 3  # 3 days


def _send_email_change_confirmation(request, user, new_email):
    """Email `new_email` a link to confirm it before it actually replaces
    user.email -- otherwise "changing" your email would just be typing in
    any address you don't have to prove you own, same gap the original
    signup flow closed with a verification link."""
    token = signing.dumps(
        {"user_id": user.pk, "new_email": new_email}, salt=_EMAIL_CHANGE_SALT
    )
    confirm_url = request.build_absolute_uri(
        reverse("confirm_email_change", kwargs={"token": token})
    )
    message = render_to_string(
        "login/email/email_change_confirmation.txt",
        {"user": user, "new_email": new_email, "confirm_url": confirm_url},
    )
    send_mail(
        subject="Confirm your new Ifi Platform email",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[new_email],
    )
    if settings.DEBUG:
        print(f"[email change confirmation] {new_email} -> {confirm_url}")


@login_required()
def account_settings_view(request):
    """Render the account settings page for the currently logged-in user,
    with an editable (optional) profile form -- see ProfileForm. Name
    changes apply immediately; an email change is held back until the new
    address is confirmed (see _send_email_change_confirmation), tracked via
    profile.pending_email so this page can show/cancel it in the meantime."""
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)
    allow_clearing = user.is_staff or user.is_superuser
    if request.method == "POST":
        # ModelForm.is_valid() mutates the bound instance in place (via
        # _post_clean() -> construct_instance()) before this view ever runs
        # -- capture the pre-change value now, or comparing user.email to
        # the submitted value below would always see them as equal.
        original_email = user.email
        form = ProfileForm(request.POST, instance=user, allow_clearing=allow_clearing)
        if form.is_valid():
            new_email = form.cleaned_data["email"]
            email_changed = new_email != (original_email or "")

            user.first_name = form.cleaned_data["first_name"]
            user.last_name = form.cleaned_data["last_name"]

            if email_changed and new_email:
                # construct_instance() (above, inside is_valid()) already
                # wrote new_email onto user.email in memory -- put the old
                # one back before saving, so only the name changes persist
                # and the address on file doesn't change until confirmed.
                user.email = original_email
                user.save()
                profile.pending_email = new_email
                profile.save(update_fields=["pending_email"])
                _send_email_change_confirmation(request, user, new_email)
                return redirect("email_change_sent")

            # unchanged, or an admin clearing it to blank (allow_clearing) --
            # nothing to confirm either way, apply directly. Also clears any
            # unrelated pending change still sitting around from earlier.
            user.email = new_email
            user.save()
            if profile.pending_email:
                profile.pending_email = ""
                profile.save(update_fields=["pending_email"])
            return redirect("account_settings")
    else:
        form = ProfileForm(instance=user, allow_clearing=allow_clearing)

    profile_incomplete = not (user.email and user.first_name and user.last_name)

    return render(
        request=request,
        template_name="core/account_settings.html",
        context={
            "user": user,
            "form": form,
            "profile_incomplete": profile_incomplete,
            "pending_email": profile.pending_email,
        },
    )


@login_required()
def cancel_email_change_view(request):
    """Drop a pending email change, leaving the current (old) address in
    place -- only meaningful while it's still unconfirmed."""
    if request.method == "POST":
        Profile.objects.filter(user=request.user).update(pending_email="")
    return redirect("account_settings")


def email_change_sent_view(request):
    """Shown after requesting an email change, telling the user to check
    the *new* address for a confirmation link."""
    return render(request=request, template_name="login/email_change_sent.html")


def confirm_email_change_view(request, token):
    """Apply a pending email change once the new address confirms it."""
    try:
        data = signing.loads(
            token, salt=_EMAIL_CHANGE_SALT, max_age=_EMAIL_CHANGE_MAX_AGE
        )
    except signing.BadSignature:
        return render(request=request, template_name="login/email_change_invalid.html")

    User = get_user_model()
    try:
        user = User.objects.get(pk=data["user_id"])
    except User.DoesNotExist:
        return render(request=request, template_name="login/email_change_invalid.html")

    new_email = data["new_email"]
    profile, _ = Profile.objects.get_or_create(user=user)
    # profile.pending_email won't match if the change was cancelled, or a
    # newer/different change was requested since this link was sent -- the
    # token alone can't tell either of those apart, so re-check here.
    if profile.pending_email != new_email:
        return render(request=request, template_name="login/email_change_invalid.html")

    # re-check uniqueness -- someone else could have taken it in the days
    # since this link was sent (the token itself has no idea).
    if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
        return render(request=request, template_name="login/email_change_invalid.html")

    user.email = new_email
    user.save(update_fields=["email"])
    profile.pending_email = ""
    profile.save(update_fields=["pending_email"])
    return render(
        request=request,
        template_name="login/email_change_success.html",
        context={"user": user},
    )
