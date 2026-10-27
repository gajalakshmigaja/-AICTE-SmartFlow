from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('', include('accounts.urls')),  # Provides /login/, /logout/, /register/, /profile/
    path('institutions/', include('institutions.urls')),
    path('documents/', include('documents.urls')),
    path('compliance/', include('compliance.urls')),
    path('notifications/', include('notifications.urls')),
    path('audit/', include('audit.urls')),
    path('', include('applications.urls')),
]