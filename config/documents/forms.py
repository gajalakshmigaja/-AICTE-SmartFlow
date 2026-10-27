from django import forms
from .models import ApplicationDocument


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = ApplicationDocument
        fields = ['document_type', 'title', 'file', 'expiry_date']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Registered Land Sale Deed'}),
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.png,.jpg,.jpeg,.doc,.docx'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class DocumentReplacementForm(forms.ModelForm):
    class Meta:
        model = ApplicationDocument
        fields = ['file', 'expiry_date']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.png,.jpg,.jpeg,.doc,.docx'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }


class DocumentVerificationForm(forms.Form):
    STATUS_CHOICES = [
        ('VERIFIED', 'Verified & Accepted'),
        ('DEFICIENT', 'Deficient (Request Replacement)'),
        ('REJECTED', 'Rejected'),
    ]

    verification_status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    reviewer_comments = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Explain verification result or specify why document is deficient...'
        }),
        required=False
    )
