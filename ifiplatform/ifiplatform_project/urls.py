"""
URL configuration for ifiplatform project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.contrib.auth import views as auth_views
from wagtail.admin import urls as wagtailadmin_urls

# language selection
urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
]

urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("wagtail-admin/", include(wagtailadmin_urls)), # admin ctrl to articles using wagtail dependancy
    path("study/", include("study_app.urls")),
    path("account/", include("account_app.urls")),
    path("yourpage/", include("yourpage_app.urls")),
    path("", include("ifi_home_app.urls")),
)
