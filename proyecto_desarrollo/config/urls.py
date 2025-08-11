
from django.contrib import admin
from django.urls import path
from django.urls import path
from busturistico.views import *
from busturistico import views

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='admin-dashboard'),

    # Choferes
    path('admin/choferes/', views.ChoferesView.as_view(), name='admin-choferes'),
    path('admin/nuevo-chofer/', views.CrearChoferView.as_view(), name='admin-nuevo-chofer'),

    # Flota (Buses)
    path('admin/flota/', views.FlotaView.as_view(), name='admin-flota'),
    path('admin/nuevo-bus/', views.CrearBusView.as_view(), name='admin-nuevo-bus'),

    # Viajes
    path('admin/viajes/', views.ViajesView.as_view(), name='admin-viajes'),
    path('admin/nuevo-viaje/', views.CrearViajeView.as_view(), name='admin-nuevo-viaje'),

    # Paradas
    path('admin/paradas/', views.ParadasView.as_view(), name='admin-paradas'),
    path('admin/nuevo-parada/', views.CrearParadaView.as_view(), name='admin-nuevo-parada'),

    # Recorridos
    path('admin/recorridos/', views.RecorridosView.as_view(), name='admin-recorridos'),
    path('admin/nuevo-recorrido/', views.CrearRecorridoView.as_view(), name='admin-nuevo-recorrido'),

    # Reportes
    path('admin/reportes/', views.ReportesView.as_view(), name='admin-reportes'),

    # Usuario público
    path('usuario/', views.BaseUsuarioView.as_view(), name='usuario-base'),
]
