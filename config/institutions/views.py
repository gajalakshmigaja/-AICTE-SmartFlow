from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST

from .models import Institution, ProgrammeCourse, FacultyMember
from .forms import InstitutionProfileForm, ProgrammeCourseForm, FacultyMemberForm
from accounts.decorators import institution_required


def get_or_create_institution(user):
    institution, created = Institution.objects.get_or_create(
        user=user,
        defaults={
            'name': f"{user.username}'s Institution",
            'contact_email': user.email,
        }
    )
    return institution


@login_required
@institution_required
def institution_profile_view(request):
    institution = get_or_create_institution(request.user)

    if request.method == 'POST':
        form = InstitutionProfileForm(request.POST, instance=institution)
        if form.is_valid():
            form.save()
            messages.success(request, 'Institution profile updated successfully.')
            return redirect('institution_profile')
    else:
        form = InstitutionProfileForm(instance=institution)

    return render(request, 'institutions/profile.html', {
        'institution': institution,
        'form': form,
    })


@login_required
@institution_required
def manage_courses_view(request):
    institution = get_or_create_institution(request.user)
    courses = institution.courses.all()

    if request.method == 'POST':
        form = ProgrammeCourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.institution = institution
            course.save()
            messages.success(request, f'Course "{course.course_name}" added successfully.')
            return redirect('manage_courses')
    else:
        form = ProgrammeCourseForm()

    return render(request, 'institutions/courses.html', {
        'institution': institution,
        'courses': courses,
        'form': form,
    })


@login_required
@institution_required
def edit_course_view(request, pk):
    institution = get_or_create_institution(request.user)
    course = get_object_or_404(ProgrammeCourse, pk=pk, institution=institution)

    if request.method == 'POST':
        form = ProgrammeCourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, f'Course "{course.course_name}" updated successfully.')
            return redirect('manage_courses')
    else:
        form = ProgrammeCourseForm(instance=course)

    return render(request, 'institutions/courses.html', {
        'institution': institution,
        'courses': institution.courses.all(),
        'form': form,
        'editing_course': course,
    })


@login_required
@institution_required
@require_POST
def delete_course_view(request, pk):
    institution = get_or_create_institution(request.user)
    course = get_object_or_404(ProgrammeCourse, pk=pk, institution=institution)
    course_name = course.course_name
    course.delete()
    messages.success(request, f'Course "{course_name}" removed.')
    return redirect('manage_courses')


@login_required
@institution_required
def manage_faculty_view(request):
    institution = get_or_create_institution(request.user)
    faculty_list = institution.faculty_members.all()

    if request.method == 'POST':
        form = FacultyMemberForm(request.POST)
        if form.is_valid():
            faculty = form.save(commit=False)
            faculty.institution = institution
            faculty.save()
            messages.success(request, f'Faculty member "{faculty.name}" added successfully.')
            return redirect('manage_faculty')
    else:
        form = FacultyMemberForm()

    return render(request, 'institutions/faculty.html', {
        'institution': institution,
        'faculty_list': faculty_list,
        'form': form,
    })


@login_required
@institution_required
def edit_faculty_view(request, pk):
    institution = get_or_create_institution(request.user)
    faculty = get_object_or_404(FacultyMember, pk=pk, institution=institution)

    if request.method == 'POST':
        form = FacultyMemberForm(request.POST, instance=faculty)
        if form.is_valid():
            form.save()
            messages.success(request, f'Faculty member "{faculty.name}" updated successfully.')
            return redirect('manage_faculty')
    else:
        form = FacultyMemberForm(instance=faculty)

    return render(request, 'institutions/faculty.html', {
        'institution': institution,
        'faculty_list': institution.faculty_members.all(),
        'form': form,
        'editing_faculty': faculty,
    })


@login_required
@institution_required
@require_POST
def delete_faculty_view(request, pk):
    institution = get_or_create_institution(request.user)
    faculty = get_object_or_404(FacultyMember, pk=pk, institution=institution)
    faculty_name = faculty.name
    faculty.delete()
    messages.success(request, f'Faculty member "{faculty_name}" removed.')
    return redirect('manage_faculty')
