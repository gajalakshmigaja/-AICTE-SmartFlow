from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.custom_login, name='login'),
    path('register/', views.register_institution, name='register'),
    path('profile/', views.profile_view, name='profile'),
    path('logout/', views.custom_logout, name='logout'),
]
