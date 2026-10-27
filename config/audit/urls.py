from django.urls import path
from . import views

urlpatterns = [
    path('', views.audit_log_list_view, name='audit_log_list'),
]
