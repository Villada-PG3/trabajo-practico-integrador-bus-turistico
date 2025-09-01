# busturistico/urls_chofer.py

from django.urls import path
from . import views_chofer

urlpatterns = [
    # All class-based views should use .as_view()
    path('recorridos/', views_chofer.ChoferRecorridosView.as_view(), name='chofer-recorridos'),
    path('recorridos/<int:pk>/iniciar/', views_chofer.IniciarRecorridoView.as_view(), name='iniciar-recorrido'),
    path('viaje-en-curso/', views_chofer.DetalleViajeView.as_view(), name='viaje-en-curso'),

    # This path is correct for your class-based view.
    path('finalizar-viaje/', views_chofer.FinalizarViajeView.as_view(), name='finalizar-viaje'),

    # This path is correct for your function-based view.
    path('viaje/<int:viaje_id>/iniciar/', views_chofer.iniciar_viaje_chofer, name='iniciar-viaje-action'),
]