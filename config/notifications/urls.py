from django.urls import path
from . import views

urlpatterns = [
    path('', views.notification_list_view, name='notifications_list'),
    path('<int:pk>/read/', views.mark_read_view, name='mark_notification_read'),
    path('read-all/', views.mark_all_read_view, name='mark_all_notifications_read'),
]
