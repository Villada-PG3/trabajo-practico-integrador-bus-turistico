from django.urls import path
from . import views_usuario

urlpatterns = [
    path('', views.UsuarioInicioView.as_view(), name='usuario-inicio'),
    path('recorridos/', views.UsuarioRecorridosView.as_view(), name='usuario-recorridos'),
    path('recorridos/<int:pk>/', views.UsuarioDetalleRecorridoView.as_view(), name='usuario-detalle-recorrido'),
    path('paradas/<int:pk>/', views.UsuarioDetalleParadaView.as_view(), name='usuario-detalle-parada'),
    path('contacto/', views.UsuarioContactoView.as_view(), name='usuario-contacto'),

]