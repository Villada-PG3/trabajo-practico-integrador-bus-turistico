from django.urls import path
from . import views

urlpatterns = [
    path('mis-viajes/', views.mis_viajes, name="mis_viajes"),
    path('recorridos/', views.recorridos, name="recorridos"),
]
    