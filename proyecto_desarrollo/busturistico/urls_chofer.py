# urls_chofer.py
from django.urls import path
from .views_chofer import ChoferRecorridosView, IniciarRecorridoView

urlpatterns = [
    # Ya no necesitas 'chofer/' porque está en el include principal
    path('recorridos/', ChoferRecorridosView.as_view(), name='chofer-recorridos'),
    path('recorridos/<int:pk>/iniciar/', IniciarRecorridoView.as_view(), name='iniciar-recorrido'),
]