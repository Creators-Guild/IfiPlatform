from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from ..forms import RegisterForm
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required


# Create your views here.
def signin_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect("signin_success")
    else: # if GET
        form = UserCreationForm()
    
    return render(
        request=request, 
        template_name="login/signin.html", 
        context={'form':form}
        )

def signin_success_view(request):
    user = request.user
    return render(
        request=request,
        template_name='login/signin_success.html',
        context={'user' : user}
    )
    

def login_view(request):
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
        request=request, 
        template_name="login/login.html", 
        context={"form" : form}
        )


def logout_view(request):    
    logout(request=request)
    
    return render(
        request=request, 
        template_name="login/logout.html"
        )
