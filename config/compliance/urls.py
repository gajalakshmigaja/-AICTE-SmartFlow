from django.urls import path
from . import views

urlpatterns = [
    path('run/<int:app_id>/', views.run_compliance_view, name='run_compliance'),
    path('rules/', views.rules_list_view, name='compliance_rules'),
    path('rules/new/', views.rule_create_view, name='create_compliance_rule'),
    path('rules/<int:pk>/edit/', views.rule_edit_view, name='edit_compliance_rule'),
    path('rules/seed/', views.seed_rules_view, name='seed_compliance_rules'),
]
