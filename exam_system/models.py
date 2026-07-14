from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator
import pytz
from django.db.models.signals import post_save
from django.dispatch import receiver

# =========================
# ROLE SYSTEM
# =========================

class Profile(models.Model):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('instructor', 'Instructor'),
    )
    TIMEZONE_CHOICES = [(tz, tz) for tz in pytz.common_timezones]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    timezone = models.CharField(max_length=50, choices=TIMEZONE_CHOICES, default='Asia/Dubai')
    

    def __str__(self):
        return self.user.username

# =========================
# SUBJECT SYSTEM
# =========================

class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True, null=True) 
    description = models.TextField(blank=True, null=True)
    
    instructor = models.ForeignKey(User, on_delete=models.CASCADE)
    students = models.ManyToManyField(User, related_name="subjects", blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        if self.code:
            return f"[{self.code}] {self.name}"
        return self.name

class SubjectAssignment(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.student.username} -> {self.subject.name}"

# =========================
# EXAM SYSTEM
# =========================

class Exam(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    duration = models.IntegerField(null=True, blank=True, help_text="Minutes allowed; ignored when duration_enabled is False.")
    duration_enabled = models.BooleanField(default=True, help_text="When disabled, students have unlimited time.")
    total_questions = models.IntegerField(
        validators=[MaxValueValidator(settings.MAX_QUESTIONS_PER_EXAM)]
    )
    randomize_questions = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True, help_text="Instructors can manually open/close an exam regardless of the time window.")
    questions = models.ManyToManyField('Question', blank=True, related_name='exams')
    is_archived = models.BooleanField(default=False)

    # Time-window availability (optional — null/blank means always open)
    available_from = models.DateTimeField(null=True, blank=True, help_text="Earliest date & time students can start the exam.")
    available_until = models.DateTimeField(null=True, blank=True, help_text="Latest date & time students can start the exam.")

    def __str__(self):
        return self.title

# =========================
# QUESTION BANK
# =========================

class Question(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    
    question_text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_answer = models.CharField(max_length=1)
    
    def __str__(self):
        return self.question_text[:50]


# =========================
# EXAM ATTEMPT
# =========================

class ExamAttempt(models.Model):
    STATUS_CHOICES = (
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    )

    student = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    
    score = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)
    percentage_score = models.FloatField(default=0.0)
    integrity_score = models.IntegerField(default=100)
    risk_level = models.CharField(max_length=20, default="LOW")
    
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.username} - {self.exam.title} ({self.status})"


# =========================
# STUDENT ANSWERS
# =========================

class StudentAnswer(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, null=True) 
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, null=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.CharField(max_length=1)
    
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return f"{self.student.username if self.student else 'Unknown'} - {self.selected_answer}"

# =========================
# EXAM RESULT
# =========================

class ExamResult(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    score = models.IntegerField()
    total_questions = models.IntegerField()
    percentage_score = models.FloatField(default=0.0)
    submitted_at = models.DateTimeField(auto_now_add=True)
    integrity_score = models.IntegerField(default=100)

    RISK_CHOICES = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    )

    risk_level = models.CharField(
        max_length=10, 
        choices=RISK_CHOICES, 
        default='LOW'
    )

    def __str__(self):
        return f"{self.student.username} - {self.exam.title}"


# =========================
# INTEGRITY LOGS
# =========================

class IntegrityLog(models.Model):
    EVENT_TYPES = (
        ('tab_switch', 'Tab Switch'),
        ('copy_attempt', 'Copy Attempt'),
        ('paste_attempt', 'Paste Attempt'),
        ('right_click', 'Right Click'),
        ('refresh', 'Refresh'),
        ('devtools', 'DevTools'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    penalty = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    is_reviewed = models.BooleanField(default=False)

    def __str__(self):
        status = "Reviewed" if self.is_reviewed else "Pending"
        return f"{self.user.username} - {self.event_type} ({status})"


# =========================
# AUTOMATION: PROFILE CREATION
# =========================

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created and not Profile.objects.filter(user=instance).exists():
        Profile.objects.create(user=instance, role='student')