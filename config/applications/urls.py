from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('applications/new/', views.create_application, name='create_application'),
    path('applications/<int:pk>/', views.application_detail, name='application_detail'),
    path('applications/<int:pk>/edit/', views.edit_application, name='edit_application'),
    path('applications/<int:pk>/submit/', views.submit_application, name='submit_application'),
    path('applications/<int:pk>/respond-deficiency/', views.respond_deficiency, name='respond_deficiency'),
    path('officer/dashboard/', views.officer_dashboard, name='officer_dashboard'),
    path('officer/review/<int:pk>/', views.officer_review, name='officer_review'),
    path('admin-portal/dashboard/', views.director_dashboard, name='director_dashboard'),
    path('api/chatbot/', views.chatbot_api_view, name='chatbot_api'),
]