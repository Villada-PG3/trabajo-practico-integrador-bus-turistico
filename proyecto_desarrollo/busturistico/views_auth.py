from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from .forms import ChoferLoginForm
from .models import Chofer


class ChoferLoginView(TemplateView):
    template_name = 'chofer/chofer_login.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('chofer-recorridos')
        
        form = ChoferLoginForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        # Corrección: Elimina 'request' del constructor
        form = ChoferLoginForm(data=request.POST) 
        
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('chofer-recorridos')
        
        return render(request, self.template_name, {'form': form})


def chofer_logout_view(request):
    logout(request)
    messages.info(request, 'Sesión cerrada correctamente.')
    return redirect('chofer-login')