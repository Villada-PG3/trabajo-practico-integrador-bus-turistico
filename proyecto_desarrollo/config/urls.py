from django.contrib import admin
from django.urls import path, include
from busturistico.views import *
from busturistico import views
from busturistico.views_usuario import *
from busturistico import views_usuario, urls_usuario
from django.conf import settings
from django.conf.urls.static import static
from busturistico import views_chofer, urls_chofer

urlpatterns = [
    path('chofer/', include('busturistico.urls_chofer')),
    # Dashboard
    path('admin/dashboard/', views.DashboardView.as_view(), name='admin-dashboard'),
    # Choferes
    path('admin/choferes/', views.ChoferesView.as_view(), name='admin-choferes'),
    path('admin/choferes/detalle/<int:pk>/', views.ChoferDetailView.as_view(), name='admin-detalle-chofer'),
    path('admin/nuevo-chofer/', views.CrearChoferView.as_view(), name='admin-nuevo-chofer'),
    path('admin/choferes/editar/<int:pk>/', views.EditarChoferView.as_view(), name='admin-editar-chofer'),
    path('admin/choferes/eliminar/<int:pk>/', views.EliminarChoferView.as_view(), name='admin-eliminar-chofer'),
    path('admin/choferes/eliminar/directo/<int:pk>/', views.eliminar_chofer_directo, name='admin-eliminar-chofer-directo'),
    # Flota (Buses)
    path('admin/flota/', views.FlotaView.as_view(), name='admin-flota'),
    path('admin/nuevo-bus/', views.CrearBusView.as_view(), name='admin-nuevo-bus'),
    path('admin/flota/<str:pk>/detalle/', views.BusDetailView.as_view(), name='admin-detalle-bus'),
    path('admin/flota/<str:pk>/editar/', views.EditarBusView.as_view(), name='admin-editar-bus'),
    path('admin/flota/<str:pk>/eliminar/', views.EliminarBusView.as_view(), name='admin-eliminar-bus'),
    path('admin/flota/<str:pk>/cambiar-estado/', views.CambiarEstadoBusView.as_view(), name='admin-cambiar-estado-bus'),
    # Atractivos
    path('admin/atractivos/', views.AtractivoView.as_view(), name='admin-atractivos'),
    path('admin/nuevo-atractivo/', views.CrearAtractivoView.as_view(), name='admin-nuevo-atractivo'),
    path('admin/atractivos/<int:pk>/detalle/', views.AtractivoDetailView.as_view(), name='admin-detalle-atractivo'),
    path('admin/atractivos/<int:pk>/editar/', views.EditarAtractivoView.as_view(), name='admin-editar-atractivo'),
    path('admin/atractivos/<int:pk>/eliminar/', views.EliminarAtractivoView.as_view(), name='admin-eliminar-atractivo'),
    # Viajes
    path('admin/viajes/', views.ViajesView.as_view(), name='admin-viajes'),
    path('admin/nuevo-viaje/', views.CrearViajeView.as_view(), name='admin-nuevo-viaje'),
    path('viajes/completar/<int:pk>/', views.completar_viaje_y_limpiar, name='completar-viaje'),
    # Paradas
    path('admin/paradas/', views.ParadasView.as_view(), name='admin-paradas'),
    path('admin/nuevo-parada/', views.CrearParadaView.as_view(), name='admin-nuevo-parada'),
    path('admin/paradas/<int:pk>/editar/', views.EditarParadaView.as_view(), name='admin-editar-parada'),
    path('admin/paradas/<int:pk>/eliminar/', views.EliminarParadaView.as_view(), name='admin-eliminar-parada'),
    path('admin/paradas/<int:pk>/detalle', views.ParadaDetailView.as_view(), name='admin-detalle-parada'),
    # Recorridos
    path('admin/recorridos/', views.RecorridosView.as_view(), name='admin-recorridos'),
    path('admin/nuevo-recorrido/', views.CrearRecorridoView.as_view(), name='admin-nuevo-recorrido'),
    path('admin/recorridos/<int:pk>/', views.RecorridoDetailView.as_view(), name='admin-detalle-recorrido'),
    path('admin/recorridos/<int:pk>/editar/', views.EditarRecorridoView.as_view(), name='admin-editar-recorrido'),
    path('admin/recorridos/<int:pk>/eliminar/', views.EliminarRecorridoView.as_view(), name='admin-eliminar-recorrido'),
    # Reportes
    path('admin/reportes/', views.ReportesView.as_view(), name='admin-reportes'),
    path('admin/generar-reporte/', views.generar_reporte, name='generar-reporte'),
    # Usuario público
    path('', include('busturistico.urls_usuario')),
    
    # Choferes
    path('auth/', include('busturistico.urls_auth')),
    
    # Admin de Django
    path('admin/', admin.site.urls),
] 

# Servir archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)