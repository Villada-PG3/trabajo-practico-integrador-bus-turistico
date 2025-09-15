from django.urls import path
from . import views_usuario
from .views_usuario import MapaView

urlpatterns = [
    path('', views_usuario.UsuarioInicioView.as_view(), name='usuario-inicio'),
    path('recorridos/', views_usuario.UsuarioRecorridosView.as_view(), name='usuario-recorridos'),
    path('recorridos/<int:pk>/', views_usuario.UsuarioDetalleRecorridoView.as_view(), name='usuario-detalle-recorrido'),
    path('paradas/<int:pk>/', views_usuario.UsuarioDetalleParadaView.as_view(), name='usuario-detalle-parada'),
    path('contacto/', views_usuario.UsuarioContactoView.as_view(), name='usuario-contacto'),
    path('mapa/', MapaView.as_view(), name='usuario-mapa'),
    path('busqueda/', views_usuario.UsuarioBusquedaView.as_view(), name='usuario-busqueda'),
]