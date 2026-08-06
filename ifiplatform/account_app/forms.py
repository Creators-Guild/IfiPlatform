"""Custom user registration form."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm


class SignupForm(UserCreationForm):
    """Registration form requiring username, email, first and last name (in
    addition to UserCreationForm's own username/password1/password2), with a
    uniqueness check on email since it's also how a user would be looked up
    for email verification/password reset."""

    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ["username", "email", "first_name", "last_name"]

    def clean_email(self):
        email = self.cleaned_data["email"]
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class ResendVerificationForm(forms.Form):
    """Just an email address -- the view looks up the matching inactive
    account (if any) itself, see resend_verification_view."""

    email = forms.EmailField(required=True)


class ProfileForm(forms.ModelForm):
    """Lets an existing user fill in/update email, first and last name from
    their account settings page. All optional (unlike SignupForm) -- this is
    a nudge for accounts that predate those becoming required at signup, not
    something existing users are forced to complete.

    Once a field has a value, a regular user can no longer blank it back out
    (only fill it in or change it) -- pass allow_clearing=True (staff/admins
    editing an account) to lift that restriction."""

    def __init__(self, *args, allow_clearing=False, **kwargs):
        self.allow_clearing = allow_clearing
        super().__init__(*args, **kwargs)
        # locked by default -- profile_edit_toggle.js removes this when the
        # matching "Edit" link is clicked. readonly (not disabled) so the
        # current value still submits as-is if left untouched.
        for field in self.fields.values():
            field.widget.attrs["readonly"] = True
            field.widget.attrs["class"] = "field-locked"

    class Meta:
        model = get_user_model()
        fields = ["email", "first_name", "last_name"]

    def _reject_blanking(self, field_name):
        value = self.cleaned_data.get(field_name, "")
        had_value_before = bool(getattr(self.instance, field_name, ""))
        if had_value_before and not value and not self.allow_clearing:
            raise forms.ValidationError("This field can't be cleared once set.")
        return value

    def clean_email(self):
        email = self._reject_blanking("email")
        if (
            email
            and get_user_model()
            .objects.filter(email__iexact=email)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_first_name(self):
        return self._reject_blanking("first_name")

    def clean_last_name(self):
        return self._reject_blanking("last_name")
