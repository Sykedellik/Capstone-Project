from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, mark_safe
from django.utils.safestring import SafeString
from .models import (
    Profile,
    Subject,
    SubjectAssignment,
    Exam,
    Question,
    ExamAttempt,
    StudentAnswer,
    IntegrityLog,
    ExamResult,
)

# ======================
# INLINE HELPERS
# (none — StudentAnswer and IntegrityLog use FK→Exam, not FK→ExamAttempt
#  so inlines are not possible; related data is surfaced via readonly fields)
# ======================


# ======================
# PROFILE
# ======================

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'timezone')
    search_fields = ('user__username',)
    list_filter = ('role',)
    ordering = ('-user__date_joined',)


# ======================
# SUBJECT
# ======================

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'instructor', 'student_count', 'exam_count', 'created_at')
    search_fields = ('name', 'code', 'instructor__username')
    list_filter = ('instructor',)
    ordering = ('name',)

    @admin.display(description='Students')
    def student_count(self, obj):
        return obj.students.count()

    @admin.display(description='Exams')
    def exam_count(self, obj):
        return obj.exam_set.count()


# ======================
# SUBJECT ASSIGNMENT
# ======================

@admin.register(SubjectAssignment)
class SubjectAssignmentAdmin(admin.ModelAdmin):
    list_display = ('subject_name', 'student_name')
    search_fields = ('student__username', 'subject__name')

    list_select_related = ('subject', 'subject__instructor')

    @admin.display(description='Subject')
    def subject_name(self, obj):
        return f"{(obj.subject.code or obj.subject.name)} – {obj.subject.instructor.username}"

    @admin.display(description='Student')
    def student_name(self, obj):
        return obj.student.username


# ======================
# EXAM
# ======================

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'subject_display', 'duration_display', 'total_questions',
        'randomize_label', 'active_badge', 'window_display',
    )
    search_fields = ('title', 'description', 'subject__name', 'subject__code')
    list_filter = ('subject', 'randomize_questions', 'is_archived', 'is_active', 'duration_enabled')
    ordering = ('-id',)
    list_select_related = ('subject', 'subject__instructor')

    def subject_display(self, obj):
        return f"{(obj.subject.code or obj.subject.name)} – {obj.subject.instructor.username}"
    subject_display.short_description  = 'Subject / Instructor'

    def duration_display(self, obj):
        if not obj.duration_enabled or not obj.duration:
            return mark_safe('<span style="color:#6b7280;">Unlimited</span>')
        return f"{obj.duration} min"
    duration_display.short_description = 'Duration'

    def randomize_label(self, obj):
        icon = '\U0001f500' if obj.randomize_questions else ''
        color = '#10b981' if obj.randomize_questions else '#9ca3af'
        return mark_safe(f'<span style="color:{color};">{icon}</span>')
    randomize_label.short_description = 'Randomize'

    def window_display(self, obj):
        parts = []
        if obj.available_from:
            parts.append(f"from {obj.available_from.strftime('%m/%d %H:%M')}")
        if obj.available_until:
            parts.append(f"until {obj.available_until.strftime('%m/%d %H:%M')}")
        return ' | '.join(parts) if parts else '–'
    window_display.short_description  = 'Window'

    def active_badge(self, obj):
        if obj.is_active:
            return mark_safe('<span style="color:#10b981;font-weight:700;">● Open</span>')
        return mark_safe('<span style="color:#dc2626;font-weight:700;">● Closed</span>')
    active_badge.short_description  = 'Active'


# ======================
# QUESTION
# ======================

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text_short', 'subject_name', 'correct_answer')
    search_fields = ('question_text', 'subject__name', 'correct_answer')
    list_filter = ('subject',)
    ordering = ('subject', 'id')

    def question_text_short(self, obj):
        return (obj.question_text[:80] + '…') if len(obj.question_text) > 80 else obj.question_text
    question_text_short.short_description = 'Question'

    def subject_name(self, obj):
        return obj.subject.name
    subject_name.short_description    = 'Subject'


# ======================
# EXAM ATTEMPT  (live + completed — the single source of truth)
# ======================

@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display       = (
        'student_name', 'exam_display', 'status_badge',
        'score', 'percentage', 'integrity_score', 'risk_level',
        'start_time', 'end_time',
    )
    list_filter        = ('status', 'risk_level', 'exam')
    search_fields      = ('student__username', 'exam__title')
    ordering           = ('-start_time',)
    list_select_related = ('student', 'exam', 'exam__subject', 'exam__subject__instructor')
    list_per_page      = 25
    date_hierarchy     = 'start_time'

    def student_name(self, obj):
        return obj.student.username
    student_name.short_description = 'Student'

    def exam_display(self, obj):
        subj = obj.exam.subject
        return f"{(subj.code or subj.name)} – {obj.exam.title}"
    exam_display.short_description = 'Exam'

    def status_badge(self, obj):
        colors = {
            'not_started': '#9ca3af',
            'in_progress':  '#3b82f6',
            'completed':    '#10b981',
        }
        color = colors.get(obj.status, '#6b7280')
        return mark_safe(f'<span style="color:{color};font-weight:700;">{obj.get_status_display()}</span>')
    status_badge.short_description = 'Status'

    def percentage(self, obj):
        if obj.total_questions:
            return f"{round((obj.score / obj.total_questions) * 100, 2)}%"
        return "0%"
    percentage.short_description = 'Percentage'
    percentage.admin_order_field = 'percentage_score'

    # ── Read-only summary fields on the change view ──────────────────────

    def answered_count(self, obj):
        return StudentAnswer.objects.filter(student=obj.student, exam=obj.exam).count()
    answered_count.short_description = 'Answers'

    def violation_summary(self, obj):
        logs = IntegrityLog.objects.filter(user=obj.student, exam=obj.exam)
        total = logs.count()
        if not total:
            return '–'
        url = f"{reverse('admin:exam_system_integritylog_changelist')}?user__id__exact={obj.student.id}&exam__id__exact={obj.exam.id}"
        return mark_safe(f'<a href="{url}" target="_blank">{total} event(s)</a>')
    violation_summary.short_description = 'Violations'

    readonly_fields = ('answered_count', 'violation_summary')
    fieldsets = (
        (None, {
            'fields': ('exam', 'student', 'status', 'score', 'integrity_score', 'risk_level', 'start_time', 'end_time'),
        }),
        ('Related data', {
            'fields': ('answered_count', 'violation_summary'),
            'classes': ('collapse',),
        }),
    )


# ======================
# INTEGRITY LOGS
# ======================

@admin.register(IntegrityLog)
class IntegrityLogAdmin(admin.ModelAdmin):
    list_display       = ('user_name', 'exam_display', 'event_type', 'penalty', 'timestamp')

    def user_name(self, obj):
        return obj.user.username
    user_name.short_description = 'Student'

    def exam_display(self, obj):
        return f"{(obj.exam.subject.code or obj.exam.subject.name)} – {obj.exam.title}"
    exam_display.short_description = 'Exam'

    @admin.action(description='Mark selected logs as reviewed')
    def mark_reviewed(self, request, queryset):
        updated = queryset.update(is_reviewed=True)
        self.message_user(request, f"{updated} log(s) marked as reviewed.")

    @admin.action(description='Mark selected logs as pending')
    def mark_unreviewed(self, request, queryset):
        updated = queryset.update(is_reviewed=False)
        self.message_user(request, f"{updated} log(s) marked as pending.")


# ======================
# STUDENT ANSWERS
# ======================

@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display       = ('student_name', 'exam_display', 'question_short', 'selected_answer', 'updated_at')
    list_filter        = ('exam', 'student')
    search_fields      = ('student__username', 'exam__title', 'question__question_text', 'selected_answer')
    ordering           = ('-updated_at',)
    list_select_related = ('student', 'exam', 'question')
    list_per_page      = 50
    date_hierarchy     = 'updated_at'

    def student_name(self, obj):
        return obj.student.username if obj.student else 'Unknown'
    student_name.short_description = 'Student'

    def exam_display(self, obj):
        return f"{(obj.exam.subject.code or obj.exam.subject.name)} – {obj.exam.title}" if obj.exam else 'Unknown Exam'
    exam_display.short_description = 'Exam'

    def question_short(self, obj):
        return (obj.question.question_text[:50] + '…') if len(obj.question.question_text) > 50 else obj.question.question_text
    question_short.short_description = 'Question'


# ======================
# EXAM RESULT
# ======================

@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = (
        'student_name', 'exam_title', 'score', 'total_questions',
        'percentage_score', 'integrity_score', 'risk_level', 'submitted_at',
    )
    list_filter = ('risk_level', 'exam', 'student')
    search_fields = ('student__username', 'exam__title', 'exam__subject__name')
    ordering = ('-submitted_at',)
    list_select_related = ('student', 'exam', 'exam__subject')
    list_per_page = 25
    date_hierarchy = 'submitted_at'

    def student_name(self, obj):
        return obj.student.username
    student_name.short_description = 'Student'

    def exam_title(self, obj):
        return obj.exam.title
    exam_title.short_description = 'Exam'

    def percentage_score_display(self, obj):
        return f"{obj.percentage_score}%"
    percentage_score_display.short_description = 'Percentage'
    percentage_score_display.admin_order_field = 'percentage_score'


# NOTE: ExamResult is now registered in Admin so orphaned rows can be
# inspected and deleted.  Export views also deduplicate by keeping only
# the latest result per (student, exam) pair.
