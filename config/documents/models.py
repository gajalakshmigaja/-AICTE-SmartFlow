import hashlib
import os
import zipfile
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError


def validate_file_security(file):
    max_size_mb = 10
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"File size exceeds maximum allowed limit of {max_size_mb} MB.")

    dangerous_extensions = [
        '.exe', '.bat', '.sh', '.bin', '.cmd', '.msi', '.vbs',
        '.ps1', '.py', '.php', '.js', '.jar', '.com'
    ]
    filename_lower = file.name.lower()
    for ext in dangerous_extensions:
        if filename_lower.endswith(ext):
            raise ValidationError(f"File type with extension '{ext}' is prohibited for security reasons.")

    extension = os.path.splitext(filename_lower)[1]
    file.seek(0)
    signature = file.read(8)
    file.seek(0)
    signatures = {
        '.pdf': signature.startswith(b'%PDF-'),
        '.png': signature.startswith(b'\x89PNG\r\n\x1a\n'),
        '.jpg': signature.startswith(b'\xff\xd8\xff'),
        '.jpeg': signature.startswith(b'\xff\xd8\xff'),
        '.doc': signature.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'),
    }
    if extension in signatures and not signatures[extension]:
        raise ValidationError("The file content does not match its extension.")
    if extension == '.docx':
        try:
            with zipfile.ZipFile(file) as document:
                if not {'[Content_Types].xml', 'word/document.xml'}.issubset(document.namelist()):
                    raise ValidationError("The file content is not a valid DOCX document.")
        except (OSError, zipfile.BadZipFile) as error:
            raise ValidationError("The file content is not a valid DOCX document.") from error
        finally:
            file.seek(0)


class ApplicationDocument(models.Model):
    DOCUMENT_TYPES = [
        ('LAND_DEED', 'Land Title & Ownership Deed / Land Use Certificate'),
        ('BUILDING_PLAN', 'Approved Building Plan & Completion / Occupancy Certificate'),
        ('FIRE_SAFETY', 'Fire and Life Safety Certificate (NOC)'),
        ('AFFILIATION_NOC', 'State Govt / Affiliating University NOC'),
        ('FACULTY_RECORDS', 'Faculty Master List, Appointment Orders & Form 16'),
        ('LAB_INVENTORY', 'Laboratory Equipment Inventory & Setup Register'),
        ('LIBRARY_REGISTER', 'Library Stock Register & E-Journal Invoices'),
        ('BARRIER_FREE_CERT', 'Barrier-free Built Environment & Ramp Certificate'),
        ('ENDOWMENT_FUND', 'Financial Audit Statement / FDR / Endowment Fund Proof'),
        ('OTHER', 'Other Regulatory Supporting Document'),
    ]

    VERIFICATION_STATUSES = [
        ('PENDING', 'Pending Verification'),
        ('VERIFIED', 'Verified & Accepted'),
        ('DEFICIENT', 'Deficient / Requires Replacement'),
        ('REJECTED', 'Rejected'),
    ]

    application = models.ForeignKey(
        'applications.Application',
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(
        max_length=40,
        choices=DOCUMENT_TYPES
    )
    title = models.CharField(max_length=200)
    file = models.FileField(
        upload_to='secure_documents/%Y/%m/',
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx']),
            validate_file_security
        ]
    )
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes")
    file_hash = models.CharField(max_length=64, blank=True, help_text="SHA-256 integrity hash")
    version = models.PositiveIntegerField(default=1)

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUSES,
        default='PENDING'
    )
    reviewer_comments = models.TextField(blank=True)
    verified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='verified_documents'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expiry date for certificates (e.g. Fire Safety NOC)"
    )

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.get_document_type_display()} (v{self.version}) - {self.application.application_number}"

    def save(self, *args, **kwargs):
        if self.file and not self.file_size:
            self.file_size = self.file.size
        if self.file and not self.file_hash:
            sha256 = hashlib.sha256()
            for chunk in self.file.chunks():
                sha256.update(chunk)
            self.file_hash = sha256.hexdigest()
        super().save(*args, **kwargs)


class AIDocumentAnalysis(models.Model):
    ANALYSIS_STATUSES = [
        ('PASS', 'Automated Checks Passed'),
        ('MISMATCH_DETECTED', 'Mismatch Detected'),
        ('MANUAL_REVIEW_REQUIRED', 'Manual Review Required'),
    ]

    document = models.OneToOneField(
        ApplicationDocument,
        on_delete=models.CASCADE,
        related_name='ai_analysis'
    )
    extracted_text_preview = models.TextField(blank=True)
    detected_institution_name = models.CharField(max_length=255, blank=True)
    detected_dates = models.JSONField(default=list, blank=True)
    detected_keywords = models.JSONField(default=list, blank=True)
    confidence_score = models.FloatField(default=0.0)
    findings = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=30,
        choices=ANALYSIS_STATUSES,
        default='MANUAL_REVIEW_REQUIRED'
    )
    disclaimer = models.CharField(
        max_length=255,
        default="AI-Assisted Finding: Requires Human Review and Verification. This analysis does not confer official statutory validation."
    )
    human_verified = models.BooleanField(default=False)
    human_verdict = models.CharField(max_length=50, blank=True)
    reviewer_notes = models.TextField(blank=True)
    analysed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AI Analysis for {self.document.title} - {self.status} ({self.confidence_score*100:.0f}%)"
