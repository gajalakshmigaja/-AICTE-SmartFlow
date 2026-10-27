from django import forms
from .models import Application


class ApplicationCreateForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = [
            'institution_name',
            'application_type',
            'academic_year',
            'total_intake',
            'total_faculty',
        ]
        widgets = {
            'institution_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter official institution name'
            }),
            'application_type': forms.Select(attrs={'class': 'form-select'}),
            'academic_year': forms.TextInput(attrs={'class': 'form-control'}),
            'total_intake': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'total_faculty': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class DeficiencyResponseForm(forms.Form):
    clarification_response = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Provide item-wise clarification addressing all deficiencies flagged by the scrutiny officer...'
        }),
        required=True,
        help_text='Explain how each deficiency has been resolved, and verify that replacement documents have been uploaded.'
    )


class OfficerReviewActionForm(forms.Form):
    ACTION_CHOICES = [
        ('IN_SCRUTINY', 'Accept for Scrutiny / Resume Review'),
        ('DEFICIENCY_FLAGGED', 'Flag Deficiencies (Return to Institution)'),
        ('APPROVED', 'Approve in SmartFlow'),
        ('REJECTED', 'Reject Application'),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'reviewActionSelect'})
    )
    comments = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter review justification, specific deficiency notes, or approval remarks...'
        }),
        required=False
    )

    def __init__(self, *args, allowed_actions=None, **kwargs):
        super().__init__(*args, **kwargs)
        if allowed_actions is not None:
            allowed_actions = set(allowed_actions)
            self.fields['action'].choices = [
                (value, label)
                for value, label in self.ACTION_CHOICES
                if value in allowed_actions
            ]

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        comments = (cleaned_data.get('comments') or '').strip()

        if action in ['DEFICIENCY_FLAGGED', 'REJECTED'] and not comments:
            self.add_error('comments', 'Detailed remarks are required when flagging deficiencies or rejecting an application.')

        return cleaned_data
