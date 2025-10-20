from django.urls import path
from . import views_api

urlpatterns = [
    # Ubicaciones y tiempo real
    path('ubicaciones/activas/', views_api.ubicaciones_activas, name='api-ubicaciones-activas'),
    path('viajes/<int:viaje_id>/ubicacion/', views_api.post_ubicacion_viaje, name='api-post-ubicacion-viaje'),

    # Recorridos y paradas
    path('recorridos/<int:pk>/proximos_horarios/', views_api.proximos_horarios_recorrido, name='api-proximos-horarios-recorrido'),
    path('recorridos/<int:pk>/paradas/', views_api.paradas_recorrido, name='api-paradas-recorrido'),
]

