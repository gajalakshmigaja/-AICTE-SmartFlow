from django.contrib import admin
from .models import Application, ApplicationHistory


class ApplicationHistoryInline(admin.TabularInline):
    model = ApplicationHistory
    extra = 0
    readonly_fields = ('previous_status', 'new_status', 'action_by', 'action_type', 'comments', 'created_at')


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'application_number',
        'institution_name',
        'application_type',
        'status',
        'applicant',
        'assigned_officer',
        'created_at',
    )
    list_filter = ('status', 'application_type', 'academic_year', 'created_at')
    search_fields = (
        'application_number',
        'institution_name',
        'applicant__username',
        'applicant__email',
    )
    readonly_fields = (
        'application_number',
        'created_at',
        'updated_at',
        'submitted_at',
        'scrutiny_started_at',
        'completed_at',
    )
    inlines = [ApplicationHistoryInline]


@admin.register(ApplicationHistory)
class ApplicationHistoryAdmin(admin.ModelAdmin):
    list_display = ('application', 'previous_status', 'new_status', 'action_by', 'action_type', 'created_at')
    list_filter = ('action_type', 'created_at')
    search_fields = ('application__application_number', 'comments', 'action_by__username')