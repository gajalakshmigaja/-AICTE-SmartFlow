from django.contrib import admin
from .models import ComplianceRule, ComplianceResult


@admin.register(ComplianceRule)
class ComplianceRuleAdmin(admin.ModelAdmin):
    list_display = ('rule_code', 'name', 'category', 'parameter_name', 'threshold_value', 'is_mandatory', 'is_active', 'is_source_verified', 'effective_date')
    list_filter = ('category', 'is_mandatory', 'is_active', 'is_source_verified')
    search_fields = ('rule_code', 'name', 'regulatory_reference')


@admin.register(ComplianceResult)
class ComplianceResultAdmin(admin.ModelAdmin):
    list_display = ('application', 'check_name', 'status', 'category', 'checked_at')
    list_filter = ('status', 'category')
    search_fields = ('application__application_number', 'check_name', 'explanation')
