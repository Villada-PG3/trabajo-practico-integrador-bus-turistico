
from django.contrib import admin
from django.urls import path, include
from busturistico.views import *
from busturistico import views


urlpatterns = [
    path('admin', views.dashboard_view, name='admin-dashboard'),
    path('choferes/', views.choferes_view, name='admin-choferes'),
    path('flota/', views.flota_view, name='admin-flota'),
    path('viajes/', views.viajes_view, name='admin-viajes'),
    path('paradas/', views.paradas_view, name='admin-paradas'),
    path('recorridos/', views.recorridos_view, name='admin-recorridos'),
    path('reportes/', views.reportes_view, name='admin-reportes'),
    path('nuevo-chofer/', views.crear_chofer, name='admin-nuevo-chofer'),
    path('nuevo-bus/', views.crear_bus, name='admin-nuevo-bus'),
    path('nuevo-viaje/', views.crear_viaje, name='admin-nuevo-viaje'),
    path('nuevo-parada/', views.crear_parada, name='admin-nuevo-parada'),
    path('nuevo-recorrido/', views.crear_recorrido, name='admin-nuevo-recorrido'),
    path('', include('busturistico.urls_usuario')),
    
]

