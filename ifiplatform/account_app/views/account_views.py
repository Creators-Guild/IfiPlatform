"""Views for account settings and user profile management."""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required()
def account_settings_view(request):
    """Render the account settings page for the currently logged-in user."""
    user = request.user
    return render(
        request=request,
        template_name="core/account_settings.html",
        context={"user": user},
    )
