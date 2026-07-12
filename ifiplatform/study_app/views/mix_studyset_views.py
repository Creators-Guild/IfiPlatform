"""Views for mixed study set feature."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect


def menu_view(request):
    """Display the mixed study set menu."""
    return render(request, "mix_studyset/core/menu.html")
