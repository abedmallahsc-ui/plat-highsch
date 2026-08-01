from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Assessment, AssessmentSubmission, FinalGradeSheet, Program, SchoolClass, Student, Subject, Teacher


class DatabaseScalingTests(TestCase):
    def test_important_lookup_fields_are_indexed(self):
        self.assertTrue(Assessment._meta.get_field('school_class').db_index)
        self.assertTrue(Assessment._meta.get_field('subject').db_index)
        self.assertTrue(AssessmentSubmission._meta.get_field('status').db_index)
        self.assertTrue(FinalGradeSheet._meta.get_field('published').db_index)


class SchoolPlatformAccessTests(TestCase):
    def setUp(self):
        self.class_a = SchoolClass.objects.create(name='Grade 10', description='Class A')
        self.class_b = SchoolClass.objects.create(name='Grade 11', description='Class B')
        self.subject = Subject.objects.create(name='Mathematics', description='Math')

        self.teacher_user = User.objects.create_user(username='teacher1', password='secret123')
        self.teacher = Teacher.objects.create(user=self.teacher_user, full_name='Mr. Smith')
        self.teacher.school_classes.add(self.class_a)
        self.teacher.subjects.add(self.subject)

        self.student_user = User.objects.create_user(username='student1', password='secret123')
        self.student = Student.objects.create(
            user=self.student_user,
            full_name='Alice Johnson',
            student_id='S-001',
            school_class=self.class_a,
        )

        self.other_student = Student.objects.create(
            user=User.objects.create_user(username='student2', password='secret123'),
            full_name='Bob Green',
            student_id='S-002',
            school_class=self.class_b,
        )

        self.assessment_a = Assessment.objects.create(
            title='Homework 1',
            assessment_type='assignment',
            subject=self.subject,
            teacher=self.teacher,
            school_class=self.class_a,
            description='Solve problems 1-10',
        )
        self.assessment_b = Assessment.objects.create(
            title='Homework 2',
            assessment_type='assignment',
            subject=self.subject,
            teacher=self.teacher,
            school_class=self.class_b,
            description='Solve problems 11-20',
        )

    def test_student_dashboard_only_shows_assessments_for_their_class(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.assessment_a.title)
        self.assertNotContains(response, self.assessment_b.title)

    def test_teacher_dashboard_only_shows_assessments_for_their_classes(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.assessment_a.title)
        self.assertNotContains(response, self.assessment_b.title)

    def test_teacher_can_review_and_mark_submission(self):
        submission = AssessmentSubmission.objects.create(
            assessment=self.assessment_a,
            student=self.student,
            content='Completed work',
            status='submitted',
        )
        self.client.force_login(self.teacher_user)
        response = self.client.post(
            reverse('review_submission', args=[submission.pk]),
            {'mark': '90', 'feedback': 'Well done'},
        )
        self.assertEqual(response.status_code, 302)
        submission.refresh_from_db()
        self.assertEqual(submission.mark, 90)
        self.assertEqual(submission.feedback, 'Well done')
        self.assertEqual(submission.status, 'reviewed')

    def test_teacher_login_with_teacher_role_redirects_to_dashboard(self):
        response = self.client.post(
            reverse('custom_login'),
            {'username': 'teacher1', 'password': 'secret123', 'role': 'teacher'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))

    def test_teacher_role_selection_is_preserved_in_login_form(self):
        response = self.client.get(reverse('login_choice'), {'role': 'teacher'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="role" value="teacher"')

    def test_teacher_login_is_inferred_from_profile_when_role_is_mismatched(self):
        response = self.client.post(
            reverse('custom_login'),
            {'username': 'teacher1', 'password': 'secret123', 'role': 'student'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))

    def test_teacher_dashboard_program_section_shows_program_content(self):
        Program.objects.create(title='Term Program', school_class=self.class_a, description='Math week')
        self.client.force_login(self.teacher_user)
        response = self.client.get(reverse('dashboard'), {'section': 'program'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Term Program')

    def test_submission_page_allows_file_and_image_uploads(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('submit_assessment', args=[self.assessment_a.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="attachment"')
        self.assertContains(response, 'name="image"')

    def test_teacher_can_submit_final_grades_for_students(self):
        self.client.force_login(self.teacher_user)
        response = self.client.post(
            reverse('upload_final_grades'),
            {
                'school_class': self.class_a.id,
                'term': 'Term 1',
                'student_1': self.student.id,
                'marks_1': '88',
                'remarks_1': 'Good work',
            },
        )
        self.assertEqual(response.status_code, 302)
        grade_sheet = FinalGradeSheet.objects.get(student=self.student, term='Term 1')
        self.assertEqual(grade_sheet.total_marks, 88)
        self.assertEqual(grade_sheet.average, 88)
        self.assertFalse(grade_sheet.published)

    def test_student_dashboard_announcements_section_shows_announcement_card(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('dashboard'), {'section': 'announcements'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Announcement')

    def test_teacher_dashboard_shows_assigned_class_selector(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="class_id"')
        self.assertContains(response, self.class_a.name)

    def test_teacher_dashboard_filters_assessments_by_selected_class(self):
        self.client.force_login(self.teacher_user)
        response = self.client.get(reverse('dashboard'), {'class_id': self.class_a.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.assessment_a.title)
        self.assertNotContains(response, self.assessment_b.title)

    def test_student_dashboard_shows_subject_selector_for_their_class(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="subject_id"')
        self.assertContains(response, self.subject.name)

    def test_student_dashboard_filters_assessments_by_selected_subject(self):
        subject_b = Subject.objects.create(name='English', description='English')
        assessment_c = Assessment.objects.create(
            title='Reading Task',
            assessment_type='assignment',
            subject=subject_b,
            teacher=self.teacher,
            school_class=self.class_a,
            description='Read chapter 1',
        )
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('dashboard'), {'subject_id': subject_b.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, assessment_c.title)
        self.assertNotContains(response, self.assessment_a.title)
