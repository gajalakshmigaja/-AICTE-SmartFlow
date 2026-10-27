from django.contrib import admin
from .models import ApplicationDocument, AIDocumentAnalysis


class AIDocumentAnalysisInline(admin.StackedInline):
    model = AIDocumentAnalysis
    extra = 0
    readonly_fields = ('extracted_text_preview', 'confidence_score', 'status', 'disclaimer', 'analysed_at')


@admin.register(ApplicationDocument)
class ApplicationDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'document_type',
        'application',
        'version',
        'verification_status',
        'uploaded_by',
        'uploaded_at'
    )
    list_filter = ('document_type', 'verification_status', 'uploaded_at')
    search_fields = ('title', 'application__application_number', 'application__institution_name')
    readonly_fields = ('file_size', 'file_hash', 'uploaded_at', 'verified_at')
    inlines = [AIDocumentAnalysisInline]


@admin.register(AIDocumentAnalysis)
class AIDocumentAnalysisAdmin(admin.ModelAdmin):
    list_display = ('document', 'status', 'confidence_score', 'human_verified', 'human_verdict', 'analysed_at')
    list_filter = ('status', 'human_verified', 'analysed_at')
