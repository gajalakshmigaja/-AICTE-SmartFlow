from django.contrib import admin
from .models import Institution, ProgrammeCourse, FacultyMember


class ProgrammeCourseInline(admin.TabularInline):
    model = ProgrammeCourse
    extra = 1


class FacultyMemberInline(admin.TabularInline):
    model = FacultyMember
    extra = 1


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'aicte_id', 'institution_type', 'state', 'district', 'contact_email', 'establishment_year')
    list_filter = ('institution_type', 'state')
    search_fields = ('name', 'aicte_id', 'contact_email', 'district')
    inlines = [ProgrammeCourseInline, FacultyMemberInline]


@admin.register(ProgrammeCourse)
class ProgrammeCourseAdmin(admin.ModelAdmin):
    list_display = ('course_name', 'institution', 'programme', 'level', 'approved_intake', 'proposed_intake')
    list_filter = ('programme', 'level')
    search_fields = ('course_name', 'institution__name')


@admin.register(FacultyMember)
class FacultyMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'institution', 'designation', 'department', 'highest_qualification', 'is_phd')
    list_filter = ('designation', 'is_phd')
    search_fields = ('name', 'institution__name', 'department')
