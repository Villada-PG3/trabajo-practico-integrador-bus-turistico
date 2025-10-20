from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
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
        show_prompt = request.session.pop('chofer_login_prompt', False)
        context = {
            'form': form,
            'show_prompt': show_prompt,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        # Corrección: Elimina 'request' del constructor
        form = ChoferLoginForm(data=request.POST) 
        
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('chofer-recorridos')
        
        context = {
            'form': form,
            'show_prompt': request.session.pop('chofer_login_prompt', False),
        }
        return render(request, self.template_name, context)


def chofer_logout_view(request):
    logout(request)
    return redirect('chofer-login')
