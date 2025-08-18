
from django.urls import path
from .views_auth import ChoferLoginView, chofer_logout_view

urlpatterns = [
    path('login/', ChoferLoginView.as_view(), name='chofer-login'),
    path('logout/', chofer_logout_view, name='chofer-logout'),
]