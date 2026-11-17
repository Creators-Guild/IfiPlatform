"""Forms for the public "Suggest an account to show here" page of the homepage's Ifi
Instagram feed (home_views.instagram_request).

Design rationale: docs/claude_context/home_instagram.md"""

import re

from django import forms
from django.utils.translation import gettext_lazy as _

from .models.instagram import (
    DEMOCRACY,
    HUMOUR,
    MEDIA,
    UNION,
    UNIVERSITY,
    InstagramAccount,
    instagram_username,
)
from .models.instagram_request import PENDING, InstagramAccountRequest

USERNAME = re.compile(r"[a-z0-9._]{1,30}")
KIND_LABELS = [
    (UNION, _("Union or association")),
    (DEMOCRACY, _("Student democracy")),
    (UNIVERSITY, _("University or department")),
    (MEDIA, _("Media")),
    (HUMOUR, _("Humour")),
]


class InstagramCheckForm(forms.Form):
    """Step 1. Meta can only read public business or creator accounts, so
    those two are required; IFI-relatedness is the one rule with exceptions
    (user, 2026-11-17)."""

    is_public = forms.BooleanField(label=_("It's public"), required=False)
    is_professional = forms.BooleanField(
        label=_("It's a business or creator account"), required=False
    )
    ifi_related = forms.BooleanField(label=_("It's related to IFI"), required=False)

    def clean(self):
        data = super().clean()
        if not (data.get("is_public") and data.get("is_professional")):
            raise forms.ValidationError(
                _(
                    "Instagram only lets us show public business or creator "
                    "accounts. Switching is free: in Instagram, go to Settings, "
                    "then Account type and tools. Then come back here."
                ),
                code="not_readable",
            )
        return data


class InstagramRequestForm(forms.ModelForm):
    """Step 2. `website` is a honeypot: hidden from people, filled in by bots."""

    website = forms.CharField(required=False)
    # Longer than a username so a pasted Instagram address fits;
    # clean_username shortens it.
    username = forms.CharField(max_length=200, label=_("Instagram username"))

    class Meta:
        model = InstagramAccountRequest
        fields = ["username", "kind", "reason", "contact_email", "ifi_related"]
        labels = {
            "kind": _("What kind of account is it?"),
            "reason": _("How is it related to IFI?"),
            "contact_email": _("Email for the answer (optional)"),
        }
        widgets = {
            "kind": forms.RadioSelect,
            "reason": forms.Textarea(attrs={"rows": 3}),
            "ifi_related": forms.HiddenInput,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kind"].choices = KIND_LABELS
        self.fields["username"].widget.attrs.update(
            {"autocapitalize": "none", "spellcheck": "false", "placeholder": "ifinavet"}
        )
        if not self.ifi_related:
            self.fields["reason"].label = _("Why should it be shown anyway?")

    @property
    def ifi_related(self):
        """What step 1 said, from the posted or the initial value."""
        value = self.data.get("ifi_related", self.initial.get("ifi_related", True))
        return value not in (False, "False", "false", "0", "")

    def clean_username(self):
        """Turns '@Name' or a pasted address into the username, and refuses
        accounts already in the feed or already requested."""
        username = instagram_username(self.cleaned_data["username"])
        if not USERNAME.fullmatch(username):
            raise forms.ValidationError(
                _("Use the name from the account's Instagram address, e.g. ifinavet.")
            )
        if InstagramAccount.objects.filter(username=username, is_active=True).exists():
            raise forms.ValidationError(
                _("@%(username)s is already in Ifi Instagram."),
                params={"username": username},
            )
        if InstagramAccountRequest.objects.filter(
            username=username, status=PENDING
        ).exists():
            raise forms.ValidationError(
                _(
                    "@%(username)s has already been requested. An admin will look at it soon."
                ),
                params={"username": username},
            )
        return username
