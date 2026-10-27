from django import forms
from .models import Institution, ProgrammeCourse, FacultyMember


class InstitutionProfileForm(forms.ModelForm):
    class Meta:
        model = Institution
        exclude = ['user', 'created_at', 'updated_at']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'aicte_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1-XXXXXXXX'}),
            'institution_type': forms.Select(attrs={'class': 'form-select'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'district': forms.TextInput(attrs={'class': 'form-control'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'establishment_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'land_area_acres': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'built_up_area_sqm': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'land_ownership_type': forms.Select(attrs={'class': 'form-select'}),
            'land_registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'library_titles': forms.NumberInput(attrs={'class': 'form-control'}),
            'library_volumes': forms.NumberInput(attrs={'class': 'form-control'}),
            'national_journals': forms.NumberInput(attrs={'class': 'form-control'}),
            'international_journals': forms.NumberInput(attrs={'class': 'form-control'}),
            'digital_library_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'total_laboratories': forms.NumberInput(attrs={'class': 'form-control'}),
            'computer_terminals': forms.NumberInput(attrs={'class': 'form-control'}),
            'internet_bandwidth_mbps': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in (
            'name',
            'state',
            'district',
            'land_area_acres',
            'built_up_area_sqm',
            'land_ownership_type',
        ):
            self.fields[field_name].required = True


class ProgrammeCourseForm(forms.ModelForm):
    class Meta:
        model = ProgrammeCourse
        exclude = ['institution']
        widgets = {
            'programme': forms.Select(attrs={'class': 'form-select'}),
            'level': forms.Select(attrs={'class': 'form-select'}),
            'course_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Computer Science & Engineering'}),
            'approved_intake': forms.NumberInput(attrs={'class': 'form-control'}),
            'proposed_intake': forms.NumberInput(attrs={'class': 'form-control'}),
            'duration_years': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class FacultyMemberForm(forms.ModelForm):
    class Meta:
        model = FacultyMember
        exclude = ['institution']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'designation': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'highest_qualification': forms.TextInput(attrs={'class': 'form-control'}),
            'is_phd': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'pan_masked': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABCDE****F'}),
            'date_of_joining': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
