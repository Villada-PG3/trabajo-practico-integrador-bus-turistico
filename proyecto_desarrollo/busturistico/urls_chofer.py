from django.urls import path
from .views_chofer import (
    ChoferRecorridosView,
    IniciarRecorridoView,
    DetalleViajeView,
    FinalizarViajeView,
)

urlpatterns = [
    # Pantalla principal del chofer (estado del viaje)
    path('recorridos/', ChoferRecorridosView.as_view(), name='chofer-recorridos'),

    # Iniciar el viaje asignado al chofer
    path('iniciar-viaje/', IniciarRecorridoView.as_view(), name='iniciar-viaje'),

    # Compatibilidad si se llega con pk de recorrido (no crea viajes nuevos)
    path('recorridos/<int:pk>/iniciar/', IniciarRecorridoView.as_view(), name='iniciar-recorrido'),

    # Ver detalle del viaje en curso
    path('viaje-en-curso/', DetalleViajeView.as_view(), name='viaje-en-curso'),

    # Finalizar el viaje en curso
    path('finalizar-viaje/', FinalizarViajeView.as_view(), name='finalizar-viaje'),
]

