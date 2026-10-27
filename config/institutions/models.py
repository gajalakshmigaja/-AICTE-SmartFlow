from django.db import models
from django.contrib.auth.models import User


class Institution(models.Model):
    INSTITUTION_TYPES = [
        ('GOVT', 'Government'),
        ('GOVT_AIDED', 'Government Aided'),
        ('SELF_FINANCING', 'Private - Self Financing'),
        ('DEEMED_UNIVERSITY', 'Deemed to be University'),
        ('STATE_UNIVERSITY', 'State University / Constituent College'),
        ('CENTRAL_UNIVERSITY', 'Central University'),
    ]

    LAND_OWNERSHIP_CHOICES = [
        ('OWNED', 'Owned by Trust / Society / Company'),
        ('LEASED', 'Leased'),
        ('GOVT_ALLOTTED', 'Government Allotted'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='institution_profile'
    )
    name = models.CharField(max_length=255)
    aicte_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="Permanent AICTE PID if existing (e.g., 1-XXXXXXXX)"
    )
    institution_type = models.CharField(
        max_length=30,
        choices=INSTITUTION_TYPES,
        default='SELF_FINANCING'
    )

    # Address & Location
    address = models.TextField(blank=True)
    state = models.CharField(max_length=100, blank=True, default='Tamil Nadu')
    district = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)

    # Contact Info
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    establishment_year = models.PositiveIntegerField(null=True, blank=True, default=2000)

    # Land & Building
    land_area_acres = models.FloatField(
        default=2.5,
        help_text="Total continuous land area in acres"
    )
    built_up_area_sqm = models.FloatField(
        default=4000.0,
        help_text="Total instructional and administrative built-up area in square meters"
    )
    land_ownership_type = models.CharField(
        max_length=30,
        choices=LAND_OWNERSHIP_CHOICES,
        default='OWNED'
    )
    land_registration_number = models.CharField(max_length=100, blank=True)

    # Library Information
    library_titles = models.PositiveIntegerField(default=1500)
    library_volumes = models.PositiveIntegerField(default=8000)
    national_journals = models.PositiveIntegerField(default=12)
    international_journals = models.PositiveIntegerField(default=6)
    digital_library_available = models.BooleanField(default=True)

    # Laboratories & Computing
    total_laboratories = models.PositiveIntegerField(default=10)
    computer_terminals = models.PositiveIntegerField(default=150)
    internet_bandwidth_mbps = models.PositiveIntegerField(default=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_institution_type_display()})"

    @property
    def total_approved_intake(self):
        return sum(c.approved_intake for c in self.courses.all())

    @property
    def total_proposed_intake(self):
        return sum(c.proposed_intake for c in self.courses.all())

    @property
    def total_faculty_count(self):
        return self.faculty_members.count()


class ProgrammeCourse(models.Model):
    PROGRAMME_CHOICES = [
        ('ENGG_TECH', 'Engineering & Technology'),
        ('MGMT', 'Management (MBA / PGDM)'),
        ('MCA', 'Computer Applications (MCA)'),
        ('PHARM', 'Pharmacy'),
        ('ARCH', 'Architecture & Planning'),
        ('APPLIED_ARTS', 'Applied Arts & Crafts'),
        ('HOTEL_MGMT', 'Hotel Management & Catering'),
    ]

    LEVEL_CHOICES = [
        ('UG', 'Under Graduate (B.Tech / B.E. / B.Pharm / B.Arch)'),
        ('PG', 'Post Graduate (M.Tech / M.E. / MBA / MCA / M.Pharm)'),
        ('DIPLOMA', 'Diploma in Engineering & Technology'),
    ]

    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name='courses'
    )
    programme = models.CharField(max_length=40, choices=PROGRAMME_CHOICES, default='ENGG_TECH')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='UG')
    course_name = models.CharField(max_length=150, help_text="e.g. Computer Science & Engineering")
    approved_intake = models.PositiveIntegerField(default=60)
    proposed_intake = models.PositiveIntegerField(default=60)
    duration_years = models.PositiveIntegerField(default=4)

    def __str__(self):
        return f"{self.course_name} ({self.get_level_display()}) - {self.proposed_intake} seats"


class FacultyMember(models.Model):
    DESIGNATION_CHOICES = [
        ('PROFESSOR', 'Professor'),
        ('ASSOC_PROF', 'Associate Professor'),
        ('ASST_PROF', 'Assistant Professor'),
        ('LECTURER', 'Lecturer / Adjunct Faculty'),
    ]

    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name='faculty_members'
    )
    name = models.CharField(max_length=150)
    designation = models.CharField(max_length=30, choices=DESIGNATION_CHOICES, default='ASST_PROF')
    department = models.CharField(max_length=100)
    highest_qualification = models.CharField(max_length=100, default='M.Tech')
    is_phd = models.BooleanField(default=False)
    pan_masked = models.CharField(max_length=20, blank=True, help_text="e.g. ABCDE****F")
    date_of_joining = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.get_designation_display()} ({self.department})"
