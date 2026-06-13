from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect


def menu_view(request):
    return render(request, "studygames/core/menu.html")
