from django.db import models
from django.contrib.auth.models import User


class SchoolClass(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    full_name = models.CharField(max_length=150)
    subjects = models.ManyToManyField(Subject, related_name='teachers')
    school_classes = models.ManyToManyField(SchoolClass, related_name='teachers')
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.full_name


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile', blank=True, null=True)
    full_name = models.CharField(max_length=150)
    student_id = models.CharField(max_length=50, unique=True)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name='students')
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.full_name} ({self.student_id})"


class Assessment(models.Model):
    TYPE_CHOICES = [
        ('exam', 'Exam'),
        ('project', 'Project'),
        ('assignment', 'Assignment'),
        ('quiz', 'Quiz'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=200)
    assessment_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assessments', db_index=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='assessments')
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name='assessments', db_index=True)
    description = models.TextField(blank=True)
    due_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    attachment = models.FileField(upload_to='assessments/', blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['school_class', 'created_at']),
            models.Index(fields=['teacher', 'created_at']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_assessment_type_display()})"


class AssessmentSubmission(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed'),
    ]

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='submissions')
    content = models.TextField(blank=True)
    attachment = models.FileField(upload_to='submissions/', blank=True, null=True)
    image = models.ImageField(upload_to='submissions/images/', blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    mark = models.PositiveIntegerField(blank=True, null=True)
    feedback = models.TextField(blank=True)

    class Meta:
        unique_together = ('assessment', 'student')
        indexes = [
            models.Index(fields=['assessment', 'status']),
            models.Index(fields=['student', 'status']),
        ]

    def __str__(self):
        return f"{self.student} -> {self.assessment}"


class Program(models.Model):
    title = models.CharField(max_length=200)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name='programs')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.school_class})"


class FinalGradeSheet(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='final_grade_sheets')
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name='final_grade_sheets')
    term = models.CharField(max_length=50)
    total_marks = models.PositiveIntegerField(default=0)
    average = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    remarks = models.TextField(blank=True)
    published = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['school_class', 'published']),
            models.Index(fields=['student', 'term']),
        ]

    def __str__(self):
        return f"{self.student.full_name} - {self.term}"

class AssessmentAttachment(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='assessments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name

class SubmittionAttachment(models.Model):
    submission = models.ForeignKey(AssessmentSubmission, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='submissions/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name

    