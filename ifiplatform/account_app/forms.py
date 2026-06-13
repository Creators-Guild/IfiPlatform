"""Custom user registration form with password confirmation validation."""
from django import forms
from django.contrib.auth import get_user_model


class RegisterForm(forms.ModelForm):
    """Form for registering a new user account with matching password fields."""
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(
        widget=forms.PasswordInput, label="Confirm Password"
    )

    class Meta:
        """Meta options for RegisterForm."""
        model = User = get_user_model()
        fields = ["username", "password", "password_confirm"]

    def clean(self):
        """Validate that the two password fields match."""
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        # check if password match
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords do not match")

        return cleaned_data
