from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Assessment, AssessmentSubmission, FinalGradeSheet, Program, SchoolClass, Student, Subject, Teacher


def teacher_allowed_subjects(teacher):
    return teacher.subjects.all()


def teacher_allowed_classes(teacher):
    return teacher.school_classes.all()


def login_choice(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    role = request.GET.get('role', 'student')
    if role not in {'student', 'teacher'}:
        role = 'student'

    return render(request, 'school/login_choice.html', {'role': role})


def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        submitted_role = request.POST.get('role') or request.GET.get('role', 'student')
        role = submitted_role if submitted_role in {'student', 'teacher'} else 'student'
        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, 'Invalid username or password.')
            return render(request, 'school/login_choice.html', {'role': role})

        has_teacher_profile = hasattr(user, 'teacher_profile')
        has_student_profile = hasattr(user, 'student_profile')

        if has_teacher_profile and not has_student_profile:
            role = 'teacher'
        elif has_student_profile and not has_teacher_profile:
            role = 'student'

        if role == 'teacher' and not has_teacher_profile and not user.is_superuser:
            messages.error(request, 'This account is not registered as a teacher.')
            return render(request, 'school/login_choice.html', {'role': role})

        if role == 'student' and not has_student_profile and not user.is_superuser:
            messages.error(request, 'This account is not registered as a student.')
            return render(request, 'school/login_choice.html', {'role': role})

        if user.is_superuser:
            login(request, user)
            return redirect('/admin/')

        login(request, user)
        return redirect('dashboard')

    return render(request, 'school/login_choice.html')


def custom_logout(request):
    logout(request)
    return redirect('login_choice')


@login_required
def dashboard(request):
    user = request.user

    if hasattr(user, 'student_profile'):
        student = user.student_profile
        class_subject_ids = Assessment.objects.filter(school_class=student.school_class).values_list('subject_id', flat=True).distinct()
        class_subjects = Subject.objects.filter(id__in=class_subject_ids).order_by('name')
        selected_subject_id = request.GET.get('subject_id')
        section = request.GET.get('section', 'assessments')
        if section not in {'assessments', 'program', 'grades', 'announcements'}:
            section = 'assessments'
        assessments = (
            Assessment.objects.filter(school_class=student.school_class)
            .select_related('subject', 'teacher', 'school_class')
            .order_by('-created_at')
        )
        if selected_subject_id:
            assessments = assessments.filter(subject_id=selected_subject_id)
        assessments = assessments[:50]
        submissions = (
            AssessmentSubmission.objects.filter(student=student)
            .select_related('assessment')
            .order_by('-submitted_at')
        )
        grade_sheets = FinalGradeSheet.objects.filter(student=student, published=True).order_by('-created_at')[:20]
        grades = submissions.filter(status='reviewed')
        context = {
            'student': student,
            'assessments': assessments,
            'submissions': submissions[:50],
            'grades': grades,
            'grade_sheets': grade_sheets,
            'programs': Program.objects.filter(school_class=student.school_class).order_by('-created_at')[:20],
            'announcement_text': 'New assessments have been published for your class.',
            'available_subjects': class_subjects,
            'selected_subject_id': selected_subject_id,
            'section': section,
        }
        return render(request, 'school/student_dashboard.html', context)

    if hasattr(user, 'teacher_profile'):
        teacher = user.teacher_profile
        class_ids = list(teacher.school_classes.values_list('id', flat=True))
        allowed_subjects = list(teacher_allowed_subjects(teacher).order_by('name'))
        allowed_classes = list(teacher_allowed_classes(teacher).order_by('name'))
        selected_class_id = request.GET.get('class_id')
        section = request.GET.get('section', 'assessments')
        if section not in {'assessments', 'program', 'grades', 'announcements'}:
            section = 'assessments'
        assessments = (
            Assessment.objects.filter(teacher=teacher, school_class__in=class_ids)
            .select_related('subject', 'teacher', 'school_class')
            .order_by('-created_at')
        )
        if selected_class_id:
            assessments = assessments.filter(school_class_id=selected_class_id)
        assessments = assessments[:50]
        submissions = (
            AssessmentSubmission.objects.filter(assessment__teacher=teacher, assessment__school_class__in=class_ids)
            .select_related('assessment', 'student')
            .order_by('-submitted_at')
        )
        if selected_class_id:
            submissions = submissions.filter(assessment__school_class_id=selected_class_id)
        submissions = submissions[:100]
        context = {
            'teacher': teacher,
            'assessments': assessments,
            'submissions': submissions,
            'programs': Program.objects.filter(school_class__in=class_ids).order_by('-created_at')[:20],
            'grade_sheets': FinalGradeSheet.objects.filter(school_class__in=class_ids, published=True).order_by('-created_at')[:20],
            'allowed_subjects': allowed_subjects,
            'allowed_classes': allowed_classes,
            'announcement_text': 'Please review student submissions and update grades.',
            'selected_class_id': selected_class_id,
            'section': section,
        }
        return render(request, 'school/teacher_dashboard.html', context)

    return redirect('/admin/')


@login_required
def submit_assessment(request, assessment_id):
    assessment = get_object_or_404(Assessment, pk=assessment_id)
    student = get_object_or_404(Student, user=request.user)

    if assessment.school_class_id != student.school_class_id:
        messages.error(request, 'You can only submit to assessments for your class.')
        return redirect('dashboard')

    if assessment.subject not in teacher_allowed_subjects(student.user.teacher_profile) if hasattr(student.user, 'teacher_profile') else True:
        pass

    submission, created = AssessmentSubmission.objects.get_or_create(assessment=assessment, student=student)
    if request.method == 'POST':
        submission.content = request.POST.get('content', '')
        if 'attachment' in request.FILES:
            submission.attachment = request.FILES['attachment']
        if 'image' in request.FILES:
            submission.image = request.FILES['image']
        submission.status = 'submitted'
        submission.save()
        messages.success(request, 'Assessment submitted successfully.')
        return redirect('dashboard')

    context = {'assessment': assessment, 'submission': submission}
    return render(request, 'school/submit_assessment.html', context)


@login_required
def create_assessment(request):
    if not hasattr(request.user, 'teacher_profile'):
        messages.error(request, 'Only teachers can create assessments.')
        return redirect('dashboard')

    teacher = request.user.teacher_profile
    allowed_subjects = teacher_allowed_subjects(teacher)
    allowed_classes = teacher_allowed_classes(teacher)

    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        class_id = request.POST.get('school_class')
        subject = get_object_or_404(Subject, pk=subject_id)
        school_class = get_object_or_404(SchoolClass, pk=class_id)

        if subject not in allowed_subjects or school_class not in allowed_classes:
            messages.error(request, 'You can only create assessments for your assigned subject and class.')
            return redirect('create_assessment')

        assessment = Assessment.objects.create(
            title=request.POST.get('title', '').strip(),
            assessment_type=request.POST.get('assessment_type', 'assignment'),
            subject=subject,
            teacher=teacher,
            school_class=school_class,
            description=request.POST.get('description', ''),
            due_date=request.POST.get('due_date') or None,
        )
        messages.success(request, 'Assessment created successfully.')
        return redirect('dashboard')

    context = {
        'allowed_subjects': allowed_subjects,
        'allowed_classes': allowed_classes,
    }
    return render(request, 'school/create_assessment.html', context)


@login_required
def review_submission(request, submission_id):
    submission = get_object_or_404(AssessmentSubmission, pk=submission_id)
    teacher = get_object_or_404(Teacher, user=request.user)

    if submission.assessment.teacher != teacher or submission.assessment.school_class not in teacher.school_classes.all():
        messages.error(request, 'You are not allowed to review this class assessment.')
        return redirect('dashboard')

    if request.method == 'POST':
        submission.mark = request.POST.get('mark') or None
        submission.feedback = request.POST.get('feedback', '')
        submission.status = 'reviewed'
        submission.save()
        messages.success(request, 'Submission reviewed successfully.')
        return redirect('dashboard')

    context = {'submission': submission}
    return render(request, 'school/review_submission.html', context)


@login_required
def upload_final_grades(request):
    if not hasattr(request.user, 'teacher_profile'):
        messages.error(request, 'Only teachers can upload final grades.')
        return redirect('dashboard')

    teacher = request.user.teacher_profile
    allowed_classes = teacher_allowed_classes(teacher)

    selected_class_id = request.GET.get('class_id') or (allowed_classes[0].id if allowed_classes else None)
    students = Student.objects.none()

    if selected_class_id:
        selected_class = get_object_or_404(SchoolClass, pk=selected_class_id)
        if selected_class not in allowed_classes:
            messages.error(request, 'You can only upload grades for your assigned class.')
            return redirect('upload_final_grades')
        students = Student.objects.filter(school_class=selected_class).order_by('full_name')[:200]

    if request.method == 'POST':
        school_class_id = request.POST.get('school_class')
        term = request.POST.get('term', '').strip()
        school_class = get_object_or_404(SchoolClass, pk=school_class_id)

        if school_class not in allowed_classes:
            messages.error(request, 'You can only upload grades for your assigned class.')
            return redirect('upload_final_grades')

        students = Student.objects.filter(school_class=school_class).order_by('full_name')[:200]
        created_count = 0
        for student in students:
            mark_value = request.POST.get(f'marks_{student.id}')
            remarks_value = request.POST.get(f'remarks_{student.id}', '').strip()
            if mark_value is None or mark_value == '':
                continue

            total_marks = int(mark_value)
            average = Decimal(str(total_marks))
            FinalGradeSheet.objects.update_or_create(
                student=student,
                school_class=school_class,
                term=term,
                defaults={
                    'total_marks': total_marks,
                    'average': average,
                    'remarks': remarks_value,
                    'published': False,
                },
            )
            created_count += 1

        if created_count:
            messages.success(request, f'Final grades submitted for {created_count} student(s).')
        else:
            messages.error(request, 'No grades were submitted.')
        return redirect('dashboard')

    context = {
        'allowed_classes': allowed_classes,
        'students': students,
        'selected_class_id': selected_class_id,
    }
    return render(request, 'school/upload_final_grades.html', context)
