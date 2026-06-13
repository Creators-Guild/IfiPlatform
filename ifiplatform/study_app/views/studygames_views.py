"""Views for study games feature."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect


def menu_view(request):
    """Display the study games menu."""
    return render(request, "studygames/core/menu.html")
