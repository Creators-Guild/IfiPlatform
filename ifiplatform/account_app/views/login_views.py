"""Views for handling user login, logout, and registration."""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm


def signin_view(request):
    """Handle new user registration using Django's built-in UserCreationForm."""
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request=request, user=user)
            return redirect("signin_success")
    else:  # if GET
        form = UserCreationForm()

    return render(
        request=request, template_name="login/signin.html", context={"form": form}
    )


def signin_success_view(request):
    """Render the registration success page for the newly created user."""
    user = request.user
    return render(
        request=request,
        template_name="login/signin_success.html",
        context={"user": user},
    )


def login_view(request):
    """Handle user login and redirect to next page or home after success."""
    if request.method == "POST":
        form = AuthenticationForm(request=request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request=request, user=user)

            # check if there was a page user
            # tried to access without being logged in
            next_url = request.GET.get("next") or request.POST.get("next")
            if next_url:
                return redirect(next_url)

            # else default redirecct
            return redirect("ifi_home")
    else:
        form = AuthenticationForm()

    return render(
        request=request, template_name="login/login.html", context={"form": form}
    )


def logout_view(request):
    """Log the current user out and render the logout confirmation page."""
    logout(request=request)

    return render(request=request, template_name="login/logout.html")
