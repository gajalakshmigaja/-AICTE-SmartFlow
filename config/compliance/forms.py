from django import forms
from .models import ComplianceRule


class ComplianceRuleForm(forms.ModelForm):
    PARAMETER_CHOICES = [
        ('student_faculty_ratio', 'Student-to-faculty ratio'),
        ('min_land_acres', 'Land area (acres)'),
        ('min_builtup_sqm', 'Built-up area (square metres)'),
        ('mandatory_doc_count', 'Verified document category count'),
        ('min_library_volumes', 'Library volumes'),
        ('min_laboratories', 'Laboratory count'),
        ('fire_safety_active', 'Fire safety certificate expiry'),
    ]

    class Meta:
        model = ComplianceRule
        fields = [
            'rule_code',
            'name',
            'category',
            'programme_category',
            'regulatory_reference',
            'effective_date',
            'parameter_name',
            'threshold_value',
            'is_mandatory',
            'is_active',
            'is_source_verified',
            'description',
        ]
        widgets = {
            'rule_code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'programme_category': forms.TextInput(attrs={'class': 'form-control'}),
            'regulatory_reference': forms.TextInput(attrs={'class': 'form-control'}),
            'effective_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'parameter_name': forms.Select(attrs={'class': 'form-select'}),
            'threshold_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'is_mandatory': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_source_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parameter_name'].choices = self.PARAMETER_CHOICES

    def clean_threshold_value(self):
        threshold = self.cleaned_data['threshold_value']
        if threshold < 0:
            raise forms.ValidationError('Threshold value must be zero or greater.')
        return threshold
