from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from institutions.models import FacultyMember, Institution, ProgrammeCourse


class InstitutionManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='institution_user',
            password='SecurePass123!',
            email='institution@example.test',
        )
        self.institution = Institution.objects.create(
            user=self.user,
            name='Original Institution',
            state='Tamil Nadu',
            district='Chennai',
        )
        self.client.force_login(self.user)

    def test_profile_changes_persist(self):
        response = self.client.post(
            reverse('institution_profile'),
            {
                'name': 'Updated Institution',
                'aicte_id': '1-12345678',
                'institution_type': 'SELF_FINANCING',
                'address': 'Updated campus address',
                'state': 'Tamil Nadu',
                'district': 'Coimbatore',
                'pincode': '641001',
                'contact_email': 'contact@example.test',
                'contact_phone': '+91 9876543210',
                'website': 'https://example.test',
                'establishment_year': 2001,
                'land_area_acres': 2.75,
                'built_up_area_sqm': 4200,
                'land_ownership_type': 'OWNED',
                'land_registration_number': 'REG-123',
                'library_titles': 1800,
                'library_volumes': 9000,
                'national_journals': 12,
                'international_journals': 6,
                'digital_library_available': 'on',
                'total_laboratories': 11,
                'computer_terminals': 150,
                'internet_bandwidth_mbps': 100,
            },
        )

        self.assertRedirects(response, reverse('institution_profile'))
        self.institution.refresh_from_db()
        self.assertEqual(self.institution.name, 'Updated Institution')
        self.assertEqual(self.institution.district, 'Coimbatore')
        self.assertEqual(self.institution.land_area_acres, 2.75)
        self.assertEqual(self.institution.library_volumes, 9000)

    def test_course_and_faculty_records_can_be_updated(self):
        course_response = self.client.post(
            reverse('manage_courses'),
            {
                'programme': 'ENGG_TECH',
                'level': 'UG',
                'course_name': 'Computer Engineering',
                'approved_intake': 60,
                'proposed_intake': 60,
                'duration_years': 4,
            },
        )
        self.assertRedirects(course_response, reverse('manage_courses'))
        course = ProgrammeCourse.objects.get(institution=self.institution)

        course_response = self.client.post(
            reverse('edit_course', kwargs={'pk': course.pk}),
            {
                'programme': 'ENGG_TECH',
                'level': 'UG',
                'course_name': 'Computer Science',
                'approved_intake': 60,
                'proposed_intake': 120,
                'duration_years': 4,
            },
        )
        self.assertRedirects(course_response, reverse('manage_courses'))
        course.refresh_from_db()
        self.assertEqual(course.course_name, 'Computer Science')
        self.assertEqual(course.proposed_intake, 120)

        faculty_response = self.client.post(
            reverse('manage_faculty'),
            {
                'name': 'Dr. Example',
                'designation': 'ASST_PROF',
                'department': 'Computer Science',
                'highest_qualification': 'Ph.D.',
                'is_phd': 'on',
                'pan_masked': 'ABCDE****F',
                'date_of_joining': '2024-07-01',
            },
        )
        self.assertRedirects(faculty_response, reverse('manage_faculty'))
        faculty = FacultyMember.objects.get(institution=self.institution)

        faculty_response = self.client.post(
            reverse('edit_faculty', kwargs={'pk': faculty.pk}),
            {
                'name': 'Dr. Updated',
                'designation': 'ASSOC_PROF',
                'department': 'Computer Science',
                'highest_qualification': 'Ph.D.',
                'is_phd': 'on',
                'pan_masked': 'ABCDE****F',
                'date_of_joining': '2023-07-01',
            },
        )
        self.assertRedirects(faculty_response, reverse('manage_faculty'))
        faculty.refresh_from_db()
        self.assertEqual(faculty.name, 'Dr. Updated')
        self.assertEqual(faculty.designation, 'ASSOC_PROF')

    def test_course_edit_is_scoped_to_the_current_institution(self):
        other_user = User.objects.create_user(
            username='other_institution',
            password='SecurePass123!',
        )
        other_institution = Institution.objects.create(
            user=other_user,
            name='Other Institution',
        )
        course = ProgrammeCourse.objects.create(
            institution=other_institution,
            course_name='Private Course',
        )

        response = self.client.get(reverse('edit_course', kwargs={'pk': course.pk}))
        self.assertEqual(response.status_code, 404)
