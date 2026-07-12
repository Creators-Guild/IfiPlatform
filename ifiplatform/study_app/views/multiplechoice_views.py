"""Views for multiple choice quiz feature."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect


def menu_view(request):
    """Display the multiple choice quiz menu."""
    return render(request, "multiplechoice/core/menu.html")
