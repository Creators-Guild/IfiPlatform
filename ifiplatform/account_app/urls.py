"""URL configuration for the account app."""

from django.urls import path
from .views import login_views
from .views import account_views

urlpatterns = [
    path("signin", login_views.signin_view, name="signin"),
    path("signin_success", login_views.signin_success_view, name="signin_success"),
    path("login", login_views.login_view, name="login"),
    path("logout", login_views.logout_view, name="logout"),
    path(
        "account_settings", account_views.account_settings_view, name="account_settings"
    ),
]
