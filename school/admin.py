from django.contrib import admin
from .models import SchoolClass, Subject, Teacher, Student, Assessment, AssessmentSubmission, Program, FinalGradeSheet


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone')
    filter_horizontal = ('subjects', 'school_classes')
    search_fields = ('full_name', 'phone')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'student_id', 'school_class', 'phone')
    list_filter = ('school_class',)
    search_fields = ('full_name', 'student_id')


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'assessment_type', 'subject', 'teacher', 'school_class', 'due_date')
    list_filter = ('assessment_type', 'subject', 'school_class', 'teacher')
    search_fields = ('title', 'description')


@admin.register(AssessmentSubmission)
class AssessmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('assessment', 'student', 'status', 'mark', 'submitted_at')
    list_filter = ('status', 'assessment__school_class')
    search_fields = ('student__full_name', 'assessment__title', 'feedback')


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('title', 'school_class', 'created_at')
    search_fields = ('title', 'description')


@admin.register(FinalGradeSheet)
class FinalGradeSheetAdmin(admin.ModelAdmin):
    list_display = ('student', 'school_class', 'term', 'total_marks', 'average', 'published')
    list_filter = ('published', 'school_class', 'term')
    search_fields = ('student__full_name', 'remarks')
    actions = ['publish_selected_grade_sheets']

    def publish_selected_grade_sheets(self, request, queryset):
        updated = queryset.update(published=True)
        self.message_user(request, f'{updated} grade sheet(s) published successfully.')

    publish_selected_grade_sheets.short_description = 'Publish selected grade sheets'
