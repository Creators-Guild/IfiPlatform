from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.
@login_required()
def main_view(request):
    user = request.user # get current user
    return render(
        request=request, 
        template_name='core/yourpage_main.html',
        context={'user' : user}
        )