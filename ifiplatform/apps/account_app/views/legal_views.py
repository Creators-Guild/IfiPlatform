"""Static legal/informational pages for account_app -- plain Django views
and templates rather than Wagtail Pages, since this is fixed text that
doesn't need CMS editing, not editorial content."""

from django.conf import settings
from django.shortcuts import render


def privacy_policy_view(request):
    """The site's privacy notice (GDPR Art. 13). retention_days is passed
    through rather than hardcoded in the template, so the two stay in sync
    if UNVERIFIED_ACCOUNT_RETENTION_DAYS is ever changed."""
    return render(
        request=request,
        template_name="legal/privacy_policy.html",
        context={"retention_days": settings.UNVERIFIED_ACCOUNT_RETENTION_DAYS},
    )


def content_terms_view(request):
    """Who owns the articles and news editors write, and how they're
    credited -- the terms account_settings_view's show_editor_notice asks
    new editors to agree to, and links here."""
    return render(request=request, template_name="legal/content_terms.html")


def cookies_and_statistics_view(request):
    """Cookies, Umami visitor statistics and the monthly site-wide totals --
    the details the short privacy policy links to."""
    return render(request=request, template_name="legal/cookies_and_statistics.html")


def data_processors_view(request):
    """The outside services that handle personal data for the site (NREC,
    Resend), linked from the privacy policy."""
    return render(request=request, template_name="legal/data_processors.html")
