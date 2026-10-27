import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile
from institutions.models import Institution, ProgrammeCourse, FacultyMember
from applications.models import Application, ApplicationHistory
from compliance.services import seed_default_compliance_rules, ComplianceEngine
from notifications.services import send_notification


class Command(BaseCommand):
    help = 'Seeds demo accounts, institution profiles, and sample applications.'

    def handle(self, *args, **options):
        self.stdout.write("Initializing AICTE SmartFlow Demo Data...")

        # 1. Seed Compliance Rules
        seed_default_compliance_rules()
        self.stdout.write(self.style.WARNING("No regulatory defaults were created; configure and verify rules manually."))

        # 2. Create Users for all 4 Roles
        users_data = [
            ('inst_user', 'inst@aicte-demo.in', 'Test@1234', 'INSTITUTION', 'Dr. Ramesh Kumar', 'Principal', 'SOUTH'),
            ('scrutiny_officer', 'officer@aicte-demo.in', 'Test@1234', 'OFFICER', 'Shri A. K. Sharma', 'Scrutiny Officer', 'SOUTH'),
            ('regional_director', 'director@aicte-demo.in', 'Test@1234', 'DIRECTOR', 'Prof. Sunita Rao', 'Regional Director', 'SOUTH'),
            ('admin_user', 'admin@aicte-demo.in', 'Test@1234', 'ADMIN', 'System Administrator', 'Portal Admin', 'HQ'),
        ]

        created_users = {}
        for username, email, pwd, role, full_name, designation, reg_office in users_data:
            user, created = User.objects.get_or_create(username=username, defaults={'email': email})
            user.set_password(pwd)
            names = full_name.split(' ', 1)
            user.first_name = names[0]
            user.last_name = names[1] if len(names) > 1 else ''
            user.is_staff = (role in ['OFFICER', 'DIRECTOR', 'ADMIN'])
            user.save()

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.designation = designation
            profile.regional_office = reg_office
            profile.phone = '+91 9876543210'
            profile.save()

            created_users[username] = user
            self.stdout.write(f"[OK] Configured user: {username} ({role})")

        # 3. Create Sample Institution for inst_user
        inst_user = created_users['inst_user']
        institution, _ = Institution.objects.get_or_create(
            user=inst_user,
            defaults={
                'name': 'National Institute of Engineering & Technology',
                'aicte_id': '1-458923011',
                'institution_type': 'SELF_FINANCING',
                'address': 'Kamarajar Salai, Guindy Industrial Estate',
                'state': 'Tamil Nadu',
                'district': 'Chennai',
                'pincode': '600025',
                'contact_email': 'contact@niet-chennai.edu.in',
                'contact_phone': '+91 44 2235 8000',
                'website': 'https://www.niet-chennai.edu.in',
                'establishment_year': 2004,
                'land_area_acres': 3.5,
                'built_up_area_sqm': 8500.0,
                'land_ownership_type': 'OWNED',
                'land_registration_number': 'REG/CHN/2004/7821',
                'library_titles': 2400,
                'library_volumes': 12500,
                'national_journals': 18,
                'international_journals': 8,
                'digital_library_available': True,
                'total_laboratories': 16,
                'computer_terminals': 240,
                'internet_bandwidth_mbps': 200,
            }
        )
        self.stdout.write("[OK] Configured sample institution profile")

        # 4. Add Courses
        courses_data = [
            ('ENGG_TECH', 'UG', 'B.Tech in Computer Science & Engineering', 60, 60, 4),
            ('ENGG_TECH', 'UG', 'B.Tech in Artificial Intelligence & Data Science', 60, 60, 4),
            ('ENGG_TECH', 'UG', 'B.Tech in Electronics & Communication Engineering', 60, 60, 4),
            ('MGMT', 'PG', 'Master of Business Administration (MBA)', 60, 60, 2),
        ]
        for prog, lvl, cname, approved, proposed, dur in courses_data:
            ProgrammeCourse.objects.get_or_create(
                institution=institution,
                course_name=cname,
                defaults={
                    'programme': prog,
                    'level': lvl,
                    'approved_intake': approved,
                    'proposed_intake': proposed,
                    'duration_years': dur,
                }
            )

        # 5. Add Faculty
        faculty_data = [
            ('Dr. V. Sundaram', 'PROFESSOR', 'Computer Science & Engineering', 'Ph.D. in CSE', True),
            ('Dr. Meenakshi Iyer', 'ASSOC_PROF', 'Computer Science & Engineering', 'Ph.D. in AI', True),
            ('Mr. K. Rajesh', 'ASST_PROF', 'Computer Science & Engineering', 'M.Tech in CSE', False),
            ('Ms. S. Priya', 'ASST_PROF', 'Artificial Intelligence', 'M.Tech in IT', False),
            ('Dr. Arvind Nair', 'PROFESSOR', 'Management Studies', 'Ph.D. in Finance', True),
            ('Mrs. Lakshmi Narayanan', 'ASSOC_PROF', 'Management Studies', 'MBA, M.Phil', False),
            ('Dr. P. Balaji', 'ASST_PROF', 'Electronics & Communication', 'Ph.D. in VLSI', True),
            ('Mr. R. Karthik', 'ASST_PROF', 'Electronics & Communication', 'M.E. in Communication Systems', False),
        ]
        for fname, desig, dept, qual, is_phd in faculty_data:
            FacultyMember.objects.get_or_create(
                institution=institution,
                name=fname,
                defaults={
                    'designation': desig,
                    'department': dept,
                    'highest_qualification': qual,
                    'is_phd': is_phd,
                }
            )

        # 6. Create Sample Applications in Different Statuses
        officer = created_users['scrutiny_officer']

        apps_seed = [
            ('EOA', '2026-2027', 'SUBMITTED', 'Formal application submitted for annual Extension of Approval (EOA).', None),
            ('INCREASE_INTAKE', '2026-2027', 'IN_SCRUTINY', 'Application for additional intake of 60 seats in Artificial Intelligence.', officer),
            ('NEW_PROGRAMME', '2026-2027', 'DEFICIENCY_FLAGGED', 'Proposed new postgraduate diploma in Cybersecurity.', officer),
        ]

        for app_type, yr, status, notes, assigned_off in apps_seed:
            app, created = Application.objects.get_or_create(
                institution=institution,
                application_type=app_type,
                academic_year=yr,
                defaults={
                    'applicant': inst_user,
                    'institution_name': institution.name,
                    'total_intake': institution.total_proposed_intake,
                    'total_faculty': institution.total_faculty_count,
                    'status': status,
                    'assigned_officer': assigned_off,
                    'deficiency_notes': 'Fire Safety NOC copy is illegible. Please re-upload high-resolution clear scan.' if status == 'DEFICIENCY_FLAGGED' else '',
                    'submitted_at': datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2),
                }
            )
            if created:
                ApplicationHistory.objects.create(
                    application=app,
                    previous_status='DRAFT',
                    new_status=status,
                    action_by=officer if assigned_off else inst_user,
                    action_type='STATUS_CHANGE',
                    comments=notes
                )
                ComplianceEngine.evaluate_application(app)

        self.stdout.write(self.style.SUCCESS("[OK] Demo applications created and compliance audits evaluated."))
        self.stdout.write(self.style.SUCCESS("\nDemo Users Ready:"))
        self.stdout.write("1. Institution User:  username: inst_user         password: Test@1234")
        self.stdout.write("2. Scrutiny Officer:  username: scrutiny_officer  password: Test@1234")
        self.stdout.write("3. Regional Director: username: regional_director password: Test@1234")
        self.stdout.write("4. System Admin:      username: admin_user        password: Test@1234")
