# urls_chofer.py
from django.urls import path
from .views_chofer import ChoferRecorridosView, IniciarRecorridoView, DetalleViajeView, FinalizarViajeView

urlpatterns = [
    path('recorridos/', ChoferRecorridosView.as_view(), name='chofer-recorridos'),
    # Mantiene compatibilidad con ruta anterior (pk de recorrido), pero ya no crea viajes nuevos
    path('recorridos/<int:pk>/iniciar/', IniciarRecorridoView.as_view(), name='iniciar-recorrido'),
    # Nueva ruta (sin pk) para iniciar el viaje asignado al chofer
    path('iniciar-viaje/', IniciarRecorridoView.as_view(), name='iniciar-viaje'),
    # Nueva URL para mostrar el detalle del viaje en curso
    path('viaje-en-curso/', DetalleViajeView.as_view(), name='viaje-en-curso'),
    # Nueva URL para finalizar el viaje
    path('finalizar-viaje/', FinalizarViajeView.as_view(), name='finalizar-viaje'),
]