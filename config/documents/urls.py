from django.urls import path
from . import views

urlpatterns = [
    path('upload/<int:app_id>/', views.upload_document_view, name='upload_document'),
    path('<int:doc_id>/replace/', views.replace_document_view, name='replace_document'),
    path('<int:doc_id>/verify/', views.verify_document_view, name='verify_document'),
    path('<int:doc_id>/download/', views.download_document_view, name='download_document'),
    path('<int:doc_id>/ai-analyze/', views.run_ai_analysis_view, name='run_ai_analysis'),
    path('<int:doc_id>/ai-verify/', views.verify_ai_finding_view, name='verify_ai_finding'),
]
