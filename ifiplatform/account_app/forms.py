from django import forms
from django.contrib.auth.models import User

# costume registerForm
class RegisterForm(forms.ModelForm):
    # fields in the form
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    
    class Meta:
        model = User
        fields = ["username", "password", "password_confirm"]
        
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        
        # check if password match
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords do not match")
        
        return cleaned_data
