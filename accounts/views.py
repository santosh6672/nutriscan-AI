from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import login
from django.views.generic.edit import CreateView

from .forms import CustomUserCreationForm, EmailAuthenticationForm
from .models import User

class SignUpView(CreateView):

    form_class = CustomUserCreationForm
    success_url = reverse_lazy('profile') # Redirect to profile on success
    template_name = 'accounts/signup.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Your account has been created successfully!")
        return response

class CustomLoginView(LoginView):
    
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    form_class = EmailAuthenticationForm

    def get_success_url(self):
        return self.get_redirect_url() or reverse_lazy("profile")

class CustomLogoutView(LogoutView):
    
    next_page = reverse_lazy("home")

    def get_next_page(self):
        messages.success(self.request, "You have been successfully logged out.")
        return super().get_next_page()

@login_required
def profile_view(request):
    return render(request, "accounts/profile.html", {
        "user": request.user,
        "bmi": request.user.bmi
    })