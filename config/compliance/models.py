from django.db import models


class ComplianceRule(models.Model):
    CATEGORY_CHOICES = [
        ('FACULTY', 'Faculty Norms & Cadre Ratio'),
        ('LAND_BUILDING', 'Land & Infrastructure Norms'),
        ('ACADEMIC', 'Library & Laboratory Norms'),
        ('DOCUMENTATION', 'Mandatory Regulatory Documentation'),
        ('ADMINISTRATIVE', 'Affiliation & Statutory Compliance'),
    ]

    rule_code = models.CharField(max_length=50, unique=True, help_text="e.g. RULE_FACULTY_RATIO")
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, default='FACULTY')
    programme_category = models.CharField(
        max_length=50,
        default='All',
        help_text="Applicable programme category, e.g. Engineering, Management, Pharmacy, All"
    )
    regulatory_reference = models.CharField(
        max_length=255,
        help_text="Exact source citation verified by an authorized administrator"
    )
    effective_date = models.DateField(help_text="Effective start date of the cited source for this rule")
    parameter_name = models.CharField(
        max_length=100,
        help_text="Parameter evaluated (e.g. student_faculty_ratio, min_land_acres, min_library_volumes)"
    )
    threshold_value = models.FloatField(
        default=0.0,
        help_text="Configurable numeric regulatory threshold value"
    )
    is_mandatory = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    is_source_verified = models.BooleanField(
        default=False,
        help_text="Enable only after checking the cited source and applicability."
    )
    description = models.TextField(blank=True)

    def __str__(self):
        return f"[{self.rule_code}] {self.name} (Ref: {self.regulatory_reference})"


class ComplianceResult(models.Model):
    STATUS_CHOICES = [
        ('PASS', 'Compliant (Pass)'),
        ('WARNING', 'Advisory (Warning)'),
        ('FAIL', 'Deficient (Fail)'),
        ('MANUAL_REVIEW_REQUIRED', 'Manual Review Required'),
    ]

    application = models.ForeignKey(
        'applications.Application',
        on_delete=models.CASCADE,
        related_name='compliance_results'
    )
    rule = models.ForeignKey(
        ComplianceRule,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    check_name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES)
    explanation = models.TextField()
    evidence_field = models.CharField(max_length=200, blank=True)
    suggested_action = models.TextField(blank=True)
    regulatory_reference = models.CharField(max_length=255, blank=True)
    checked_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.application.application_number} - {self.check_name}: {self.status}"
