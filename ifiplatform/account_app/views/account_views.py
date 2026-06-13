from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required()
def account_settings_view(request):
    user = request.user
    return render(
        request=request,
        template_name="core/account_settings.html",
        context={"user": user},
    )
