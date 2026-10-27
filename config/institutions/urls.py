from django.urls import path
from . import views

urlpatterns = [
    path('profile/', views.institution_profile_view, name='institution_profile'),
    path('courses/', views.manage_courses_view, name='manage_courses'),
    path('courses/<int:pk>/edit/', views.edit_course_view, name='edit_course'),
    path('courses/<int:pk>/delete/', views.delete_course_view, name='delete_course'),
    path('faculty/', views.manage_faculty_view, name='manage_faculty'),
    path('faculty/<int:pk>/edit/', views.edit_faculty_view, name='edit_faculty'),
    path('faculty/<int:pk>/delete/', views.delete_faculty_view, name='delete_faculty'),
]
