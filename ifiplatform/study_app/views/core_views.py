from django.shortcuts import render


def main_view(request):
    return render(request=request, template_name="core/study_main.html")
