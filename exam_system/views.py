import csv
import pytz
from datetime import datetime
from django.db import transaction
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Avg, Q, Subquery, OuterRef, IntegerField, F, Value
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.contrib import messages

# MODELS
from .models import Profile, Subject, Question, Exam, ExamResult, IntegrityLog, SubjectAssignment, ExamAttempt, StudentAnswer

# DECORATORS
from .decorators import instructor_required, student_required

# =========================
# HELPERS
# =========================

def parse_datetime(value):
    """Parse a 'YYYY-MM-DD HH:MM' string from an HTML datetime-local input into a naive datetime."""
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None

def _now():
    """Return timezone-aware now."""
    return timezone.now()

def _window_closed(exam):
    """Return True if the exam is manually inactive OR the time window is closed."""
    if not exam.is_active:
        return True
    now = _now()
    if exam.available_from and now < exam.available_from:
        return True
    if exam.available_until and now > exam.available_until:
        return True
    return False

def logs_to_total(logs):
    """Return the sum of penalty for a queryset or list of IntegrityLog objects."""
    return sum(getattr(log, 'penalty', 0) for log in logs)

# =========================
# AUTH & REDIRECTION
# =========================

@login_required
def home(request):
    profile = Profile.objects.get(user=request.user)
    
    import pytz
    user_tz = pytz.timezone(profile.timezone)
    timezone.activate(user_tz)

    if profile.role == 'student':
        return redirect('student_dashboard')
    else:
        return redirect('instructor_dashboard')


def login_view(request):
    from django.contrib.auth import authenticate, login
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role', 'student')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            if hasattr(user, 'profile'):
                if role == 'instructor' and user.profile.role != 'instructor':
                    messages.error(request, "This is a student account. Please use the Student login.")
                    return redirect('login')
                if role == 'student' and user.profile.role == 'instructor':
                    messages.error(request, "This is an instructor account. Please use the Instructor login.")
                    return redirect('login')
                    
                if user.profile.role == 'instructor':
                    return redirect('instructor_dashboard')
                else:
                    return redirect('student_dashboard')
            else:
                return redirect('student_dashboard')
        else:
            messages.error(request, "Invalid username or password. Please check your credentials and try again.")
            return redirect('login')
    
    return render(request, 'login.html')

def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('login')

@login_required
def profile(request):
    profile = Profile.objects.get(user=request.user)
    
    if profile.role == 'instructor':
        subject_count = Subject.objects.filter(instructor=request.user).count()
        exam_count = Exam.objects.filter(subject__instructor=request.user).count()
        question_count = Question.objects.filter(subject__instructor=request.user).count()
    else:
        subject_count = SubjectAssignment.objects.filter(student=request.user).count()
        exam_count = ExamAttempt.objects.filter(student=request.user, status='completed').count()
        question_count = 0

    return render(request, 'profile.html', {
        'profile': profile,
        'subject_count': subject_count,
        'exam_count': exam_count,
        'question_count': question_count
    })


# =========================
# DASHBOARDS
# =========================

@login_required
def available_exams(request):
    profile = Profile.objects.get(user=request.user)

    if profile.role != 'student':
        return redirect('home')

    assignments = SubjectAssignment.objects.filter(student=request.user).select_related('subject')
    available = []
    taken = []

    for assignment in assignments:
        subject = assignment.subject
        exams = Exam.objects.filter(subject=subject, is_archived=False)
        for exam in exams:
            # Enforce availability window
            if _window_closed(exam):
                # Treat as already taken so it doesn't leak as accessible
                taken.append({'exam': exam, 'subject': subject})
                continue

            attempt = ExamAttempt.objects.filter(student=request.user, exam=exam).first()
            if attempt and attempt.status == 'completed':
                taken.append({'exam': exam, 'subject': subject})
            else:
                available.append({'exam': exam, 'subject': subject})

    total_available = len(available)
    total_taken = len(taken)

    return render(request, 'available_exams.html', {
        'available': available,
        'taken': taken,
        'total_available': total_available,
        'total_taken': total_taken
    })


@login_required
def already_taken(request):
    profile = Profile.objects.get(user=request.user)

    if profile.role != 'student':
        return redirect('home')

    attempts = ExamAttempt.objects.filter(
        student=request.user,
        status='completed'
    ).select_related('exam', 'exam__subject').order_by('-start_time')

    result_map = {
        r.exam_id: r.id
        for r in ExamResult.objects.filter(
            student=request.user,
            exam_id__in=[a.exam_id for a in attempts]
        )
    }

    for a in attempts:
        a.result_id = result_map.get(a.exam_id)

    return render(request, 'already_taken.html', {
        'results': attempts,
    })


@login_required
def student_dashboard(request):
    assignments = SubjectAssignment.objects.filter(student=request.user).select_related('subject', 'subject__instructor')

    # Prefetch attempts and answers to avoid N+1 problem
    attempts = ExamAttempt.objects.filter(student=request.user)
    attempt_dict = {a.exam_id: a for a in attempts}
    
    answers = StudentAnswer.objects.filter(student=request.user)
    answer_count_by_exam = {}
    for ans in answers:
        if ans.exam_id not in answer_count_by_exam:
            answer_count_by_exam[ans.exam_id] = 0
        answer_count_by_exam[ans.exam_id] += 1

    data = []
    total_available = 0
    total_completed = 0

    for assignment in assignments:
        subject = assignment.subject
        exams = Exam.objects.filter(subject=subject, is_archived=False)

        exam_list = []

        for exam in exams:
            attempt = attempt_dict.get(exam.id)

            if attempt:
                if attempt.status == 'completed':
                    status = 'Completed'
                    total_completed += 1
                    progress = 100
                elif _window_closed(exam):
                    status = 'Not Available'
                    progress = 0
                else:
                    status = 'In Progress'
                    answered = answer_count_by_exam.get(exam.id, 0)
                    progress = int((answered / exam.total_questions) * 100) if exam.total_questions else 0
            else:
                status = 'Not Started'
                total_available += 1
                progress = 0

            exam_list.append({
                'exam': exam,
                'status': status,
                'progress': progress
            })

        data.append({
            'subject': subject,
            'exams': exam_list,
            'count': len(exam_list)
        })

    completed_attempts = ExamAttempt.objects.filter(
        student=request.user,
        status='completed'
    ).aggregate(avg_score=Avg('score'))

    avg_score = completed_attempts.get('avg_score')

    return render(request, 'student_dashboard.html', {
        'data': data,
        'total_available': total_available,
        'total_completed': total_completed,
        'avg_score': avg_score
    })


@login_required
@instructor_required
def instructor_dashboard(request):
    subjects = Subject.objects.filter(instructor=request.user).annotate(enrolled_count=Count('subjectassignment'))
    exams = Exam.objects.filter(subject__instructor=request.user, is_archived=False).select_related('subject', 'subject__instructor')
    archived_count = Exam.objects.filter(subject__instructor=request.user, is_archived=True).count()
    subjects_count = subjects.count()
    
    recent_attempts = ExamAttempt.objects.filter(
        exam__subject__instructor=request.user
    ).select_related('student', 'exam', 'exam__subject').order_by('-start_time')[:10]
    
    total_students = SubjectAssignment.objects.filter(subject__instructor=request.user).count()
    total_questions = Question.objects.filter(subject__instructor=request.user).count()

    return render(request, 'instructor_dashboard.html', {
        'subjects': subjects,
        'exams': exams,
        'archived_count': archived_count,
        'subjects_count': subjects_count,
        'recent_attempts': recent_attempts,
        'total_students': total_students,
        'total_questions': total_questions,
    })


# =========================
# QUESTION BANK SYSTEM
# =========================

@login_required
@instructor_required
def add_question(request):
    subjects = Subject.objects.filter(instructor=request.user)
    subject = None
    exam = None
    
    # Get subject_id and exam_id from query string if provided
    subject_id = request.GET.get('subject_id')
    exam_id = request.GET.get('exam_id')
    if subject_id:
        subject = Subject.objects.get(id=subject_id)
    if exam_id:
        exam = get_object_or_404(Exam, id=exam_id, subject__instructor=request.user)

    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        subject = Subject.objects.get(id=subject_id)
        exam_id = request.POST.get('exam')
        exam = None
        if exam_id:
            exam = Exam.objects.filter(id=exam_id, subject=subject).first()

        new_question = Question.objects.create(
            subject=subject,
            question_text=request.POST['question_text'],
            option_a=request.POST['option_a'],
            option_b=request.POST['option_b'],
            option_c=request.POST['option_c'],
            option_d=request.POST['option_d'],
            correct_answer=request.POST['correct_answer']
        )

        if exam:
            exam.questions.add(new_question)
            messages.success(request, "New question added to the bank and assigned to the exam.")
            return redirect('manage_exam', exam_id=exam.id)

        messages.success(request, "New question added to the bank.")
        return redirect('question_bank')

    return render(request, 'add_question.html', {
        'subjects': subjects,
        'subject': subject,
        'exam': exam
    })


@login_required
@instructor_required
def question_bank(request):
    subjects = Subject.objects.filter(instructor=request.user)
    subject = None
    exam = None
    exam_question_ids = []
    
    # Get subject_id and exam_id from query string if provided
    subject_id = request.GET.get('subject_id')
    exam_id = request.GET.get('exam_id')

    if exam_id:
        exam = get_object_or_404(Exam, id=exam_id, subject__instructor=request.user)
        subject = exam.subject
        questions = Question.objects.filter(subject=subject).select_related('subject')
        exam_question_ids = list(exam.questions.values_list('id', flat=True))
    elif subject_id:
        try:
            subject = Subject.objects.get(id=subject_id, instructor=request.user)
        except Subject.DoesNotExist:
            subject = None
        if subject:
            questions = Question.objects.filter(subject=subject).select_related('subject')
        else:
            questions = Question.objects.none()
    else:
        subject = None
        questions = Question.objects.filter(subject__in=subjects).select_related('subject')

    return render(request, 'question_bank.html', {
        'questions': questions,
        'subject': subject,
        'exam': exam,
        'exam_question_ids': exam_question_ids,
        'subjects': subjects,
    })

@login_required
@instructor_required
def delete_question(request, question_id):
    Question.objects.get(id=question_id).delete()

    messages.success(request, "Question deleted successfully.")
    return redirect('question_bank')

@login_required
@instructor_required
def edit_question(request, question_id):
    question = Question.objects.get(id=question_id)

    if question.subject.instructor != request.user:
        return redirect('instructor_dashboard')

    if request.method == 'POST':
        question.question_text = request.POST['question_text']
        question.option_a = request.POST['option_a']
        question.option_b = request.POST['option_b']
        question.option_c = request.POST['option_c']
        question.option_d = request.POST['option_d']
        question.correct_answer = request.POST['correct_answer']

        question.save()

        messages.success(request, "Question updated successfully.")

        return redirect('question_bank')

    return render(request, 'edit_question.html', {
        'question': question
    })


# =========================
# EXAM CREATION SYSTEM
# =========================

@login_required
@instructor_required
def create_exam(request):
    profile = Profile.objects.get(user=request.user)

    if profile.role != 'instructor':
        return redirect('home')

    subjects = Subject.objects.filter(instructor=request.user)
    exams = Exam.objects.filter(subject__instructor=request.user, is_archived=False).prefetch_related('questions').order_by('-id')

    if request.method == 'POST':
        subject_id = request.POST['subject']
        title = request.POST['title']
        duration = request.POST.get('duration', '').strip()
        duration_enabled = request.POST.get('duration_enabled') == 'on'
        total_questions = request.POST['total_questions']
        randomize = request.POST.get('randomize') == 'on'
        available_from_raw = request.POST.get('available_from', '').strip()
        available_until_raw = request.POST.get('available_until', '').strip()

        # When duration_enabled is off the field is disabled → empty string is fine
        if duration_enabled and not duration:
            messages.error(request, "Duration is required when the time limit is enabled.")
            return redirect('create_exam')

        duration_val = int(duration) if duration_enabled and duration else None

        subject = Subject.objects.get(id=subject_id)

        new_exam = Exam.objects.create(
            subject=subject,
            title=title,
            duration=duration_val,
            duration_enabled=duration_enabled,
            total_questions=total_questions,
            randomize_questions=randomize,
            available_from=parse_datetime(available_from_raw),
            available_until=parse_datetime(available_until_raw),
        )

        messages.success(request, f"Exam '{title}' initialized! Please add questions.")

        return redirect('manage_exam', exam_id=new_exam.id)

    return render(request, 'create_exam.html', {'subjects': subjects, 'exams': exams})


@login_required
@instructor_required
def manage_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    subjects = Subject.objects.filter(instructor=request.user)

    if exam.subject.instructor != request.user:
        return redirect('instructor_dashboard')

    questions = exam.questions.all()
    bank_count = Question.objects.filter(subject=exam.subject).count()

    return render(request, 'manage_exam.html', {
        'exam': exam,
        'subjects': subjects,
        'questions': questions,
        'bank_count': bank_count,
    })

@login_required
@instructor_required
def update_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    if exam.subject.instructor != request.user:
        return redirect('instructor_dashboard')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        subject_id = request.POST.get('subject')
        description = request.POST.get('description', '').strip()
        duration = request.POST.get('duration')
        duration_enabled = request.POST.get('duration_enabled') == 'on'
        total_questions = request.POST.get('total_questions')
        randomize = request.POST.get('randomize') == 'on'
        available_from_raw = request.POST.get('available_from', '').strip()
        available_until_raw = request.POST.get('available_until', '').strip()

        if not title or not subject_id or not total_questions:
            messages.error(request, "All required fields must be filled in.")
            return redirect('manage_exam', exam_id=exam.id)

        subject = get_object_or_404(Subject, id=subject_id, instructor=request.user)

        exam.title = title
        exam.subject = subject
        exam.description = description
        if duration_enabled and duration:
            exam.duration = int(duration)
        exam.duration_enabled = duration_enabled
        exam.total_questions = int(total_questions)
        exam.randomize_questions = randomize
        exam.available_from = parse_datetime(available_from_raw) if available_from_raw else None
        exam.available_until = parse_datetime(available_until_raw) if available_until_raw else None
        exam.save()

        messages.success(request, f"Exam '{exam.title}' updated successfully.")
        return redirect('manage_exam', exam_id=exam.id)

    return redirect('manage_exam', exam_id=exam.id)

@login_required
@instructor_required
def add_question_to_exam(request, exam_id, question_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if exam.subject.instructor != request.user:
        return redirect('instructor_dashboard')

    question = get_object_or_404(Question, id=question_id, subject=exam.subject)
    exam.questions.add(question)
    messages.success(request, "Question added to the exam.")
    return redirect('manage_exam', exam_id=exam.id)

@login_required
@instructor_required
def remove_question_from_exam(request, exam_id, question_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if exam.subject.instructor != request.user:
        return redirect('instructor_dashboard')

    question = get_object_or_404(Question, id=question_id, subject=exam.subject)
    exam.questions.remove(question)
    messages.success(request, "Question removed from the exam.")
    return redirect('manage_exam', exam_id=exam.id)


# ── Duplicate Exam ────────────────────────────────────────────────────────────

@login_required
@instructor_required
def duplicate_exam(request, exam_id):
    original = get_object_or_404(Exam, id=exam_id)

    with transaction.atomic():
        exam = Exam.objects.create(
            subject=original.subject,
            title=original.title + (' (Copy)' if not original.title.endswith(' (Copy)') else ''),
            description=original.description,
            duration=original.duration,
            duration_enabled=original.duration_enabled,
            total_questions=original.total_questions,
            randomize_questions=original.randomize_questions,
            available_from=original.available_from,
            available_until=original.available_until,
        )
        exam.questions.set(original.questions.all())

    messages.success(request, f"Exam '{exam.title}' duplicated successfully.")
    return redirect('manage_exam', exam_id=exam.id)


# ── Toggle exam active / inactive ─────────────────────────────────────────────

@login_required
@instructor_required
def toggle_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if exam.subject.instructor != request.user:
        messages.error(request, "You can only toggle your own exams.")
        return redirect('instructor_dashboard')

    exam.is_active = not exam.is_active
    exam.save()

    state = 'opened' if exam.is_active else 'closed'
    messages.success(request, f"Exam '{exam.title}' is now {state}.")
    return redirect('manage_exam', exam_id=exam.id)


# ── Bulk add questions from bank ──────────────────────────────────────────────

@login_required
@instructor_required
def add_questions_to_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if exam.subject.instructor != request.user:
        return redirect('instructor_dashboard')

    already_in = set(exam.questions.values_list('id', flat=True))
    subjects = Subject.objects.filter(instructor=request.user)

    if request.method == 'POST':
        selected_ids = [int(i) for i in request.POST.getlist('questions') if i.isdigit()]
        added = 0
        for qid in selected_ids:
            if qid not in already_in:
                q = get_object_or_404(Question, id=qid, subject=exam.subject)
                exam.questions.add(q)
                added += 1
        messages.success(request, f"{added} question(s) added to the exam." if added else "No new questions added.")
        return redirect('manage_exam', exam_id=exam.id)

    subject_id = request.GET.get('subject_id', '')
    qs = Question.objects.filter(subject=exam.subject).select_related('subject')
    if subject_id:
        qs = qs.filter(subject_id=subject_id)

    questions = qs.exclude(id__in=already_in).order_by('subject__name', 'id')

    return render(request, 'add_questions_to_exam.html', {
        'exam': exam,
        'questions': questions,
        'subjects': subjects,
        'selected_subject_id': subject_id,
    })


# =========================
# SUBJECT MANAGEMENT SYSTEM
# =========================

@login_required
@instructor_required
def subjects(request):
    subjects_list = Subject.objects.filter(instructor=request.user).order_by('-created_at', 'name')
    
    # Calculate counts manually for each subject
    subjects_data = []
    total_exams = 0
    total_students = 0
    
    for subject in subjects_list:
        exam_count = subject.exam_set.filter(is_archived=False).count()
        enrolled_count = subject.subjectassignment_set.count()
        subjects_data.append({
            'id': subject.id,
            'name': subject.name,
            'code': subject.code,
            'description': subject.description,
            'exam_count': exam_count,
            'enrolled_count': enrolled_count,
            'created_at': subject.created_at,
        })
        total_exams += exam_count
        total_students += enrolled_count
    
    return render(request, 'subjects.html', {
        'subjects': subjects_data,
        'total_exams': total_exams,
        'total_students': total_students
    })


@login_required
@student_required
def certificate(request, result_id):
    result = get_object_or_404(ExamResult, id=result_id, student=request.user)
    attempt = ExamAttempt.objects.filter(student=request.user, exam=result.exam, status='completed').first()
    if not attempt:
        return redirect('my_results')

    return render(request, 'certificate.html', {
        'result': result,
        'attempt': attempt,
        'student': result.student,
        'exam': result.exam,
        'subject': result.exam.subject,
    })


@login_required
def student_subjects(request):
    profile = Profile.objects.get(user=request.user)
    
    if profile.role != 'student':
        return redirect('home')
    
    assignments = SubjectAssignment.objects.filter(student=request.user).select_related('subject', 'subject__instructor')
    subjects_data = []
    
    for assignment in assignments:
        subject = assignment.subject
        exam_count = Exam.objects.filter(subject=subject, is_archived=False).count()
        enrolled_count = SubjectAssignment.objects.filter(subject=subject).count()
        subjects_data.append({
            'id': subject.id,
            'name': subject.name,
            'code': subject.code,
            'instructor': subject.instructor,
            'exam_count': exam_count,
            'enrolled_count': enrolled_count,
        })
    
    return render(request, 'student_subjects.html', {'subjects': subjects_data})


@login_required
@instructor_required
def create_subject(request):
    subjects = Subject.objects.filter(instructor=request.user).annotate(
        exam_count=Count('exam'),
        question_count=Count('question'),
        enrolled_count=Count('subjectassignment')
    ).order_by('-created_at', 'name')

    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        description = request.POST.get('description')

        Subject.objects.create(
            name=name,
            code=code,
            description=description,
            instructor=request.user
        )

        messages.success(request, f"Subject '{name}' created successfully!")

        return redirect('create_subject')

    return render(request, 'create_subject.html', {
        'subjects': subjects,
        'total_exams': sum(s.exam_count for s in subjects),
        'total_students': sum(s.enrolled_count for s in subjects)
    })


@login_required
@instructor_required
def delete_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id, instructor=request.user)
    subject_name = subject.name
    subject.delete()
    messages.success(request, f"Subject '{subject_name}' has been deleted.")
    return redirect('create_subject')


@login_required
@instructor_required
def edit_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id, instructor=request.user)
    
    if request.method == 'POST':
        subject.name = request.POST.get('name')
        subject.code = request.POST.get('code')
        subject.description = request.POST.get('description')
        subject.save()
        messages.success(request, f"Subject '{subject.name}' updated successfully!")
        return redirect('manage_subject', subject.id)
    
    return render(request, 'edit_subject.html', {'subject': subject})


@login_required
@instructor_required
def manage_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id, instructor=request.user)
    exams = Exam.objects.filter(subject=subject).order_by('-id')
    questions = Question.objects.filter(subject=subject).order_by('-id')
    students = SubjectAssignment.objects.filter(subject=subject).select_related('student').order_by('student__username')

    return render(request, 'manage_subject.html', {
        'subject': subject,
        'exams': exams,
        'questions': questions,
        'students': students,
    })


# =========================
# SUBJECT ASSIGNMENT SYSTEM
# =========================

@login_required
@instructor_required
def assign_students(request):
    subjects = list(Subject.objects.filter(instructor=request.user).order_by('name'))
    students = list(User.objects.filter(profile__role='student').order_by('username'))

    qs = SubjectAssignment.objects.filter(
        subject__instructor=request.user
    ).select_related('subject', 'student').order_by('-id')

    items = [
        {
            'id': a.id,
            'student': a.student,
            'subject': a.subject,
        }
        for a in qs
    ]

    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        student_username = request.POST.get('student_username', '').strip()

        try:
            subject = Subject.objects.get(id=subject_id, instructor=request.user)
            student = User.objects.get(username=student_username, profile__role='student')
            SubjectAssignment.objects.get_or_create(subject=subject, student=student)
            subject.students.add(student)
            messages.success(request, f"Student '{student_username}' successfully enrolled!")
        except (Subject.DoesNotExist, User.DoesNotExist):
            messages.error(request, "Student not found. Please select a valid student from the list.")

        return redirect('assign_students')

    return render(request, 'assign_students.html', {
        'subjects': subjects,
        'students': students,
        'enrolled_items': items,
    })

@login_required
@instructor_required
def remove_student(request, assignment_id):
    assignment = SubjectAssignment.objects.get(id=assignment_id)
    
    if assignment.subject.instructor == request.user:
        assignment.subject.students.remove(assignment.student)
        assignment.delete()
        messages.success(request, "Student removed from subject successfully.")
    
    return redirect('assign_students')


# =========================
# EXAM GUIDELINES CONFIRMATION
# =========================

@login_required
@student_required
def exam_guidelines(request, exam_id):
    exam = Exam.objects.get(id=exam_id)

    is_assigned = SubjectAssignment.objects.filter(subject=exam.subject, student=request.user).exists()
    if not is_assigned:
        return redirect('student_dashboard')

    attempt = ExamAttempt.objects.filter(student=request.user, exam=exam).first()
    if attempt and attempt.status == 'completed':
        return redirect('already_taken')

    if request.method == 'POST':
        request.session[f'exam_guidelines_ack_{exam_id}'] = True
        request.session['exam_guidelines_exam_id'] = exam_id
        return redirect('start_exam', exam_id=exam_id)

    return render(request, 'exam_guidelines.html', {'exam': exam})


# =========================
# START EXAM
# =========================

@login_required
@student_required
def start_exam(request, exam_id):
    exam = Exam.objects.get(id=exam_id)

    # Enforce availability window first
    if _window_closed(exam):
        return render(request, 'exam_closed.html', {'exam': exam}, status=403)

    # Check assignment
    is_assigned = SubjectAssignment.objects.filter(subject=exam.subject, student=request.user).exists()
    if not is_assigned:
        return redirect('student_dashboard')

    # Get or create attempt
    attempt, created = ExamAttempt.objects.get_or_create(
        student=request.user,
        exam=exam,
        defaults={'status': 'in_progress'}
    )

    # If already completed, show result
    if attempt.status == 'completed':
        existing_result = ExamResult.objects.filter(student=request.user, exam=exam).first()
        return render(request, 'already_taken.html', {'result': existing_result})

    # Check guidelines acknowledgment - only require for new attempts
    guidelines_key = f'exam_guidelines_ack_{exam_id}'
    if not request.session.get(guidelines_key) and created:
        return redirect('exam_guidelines', exam_id=exam_id)

    # Calculate remaining time from backend
    if exam.duration_enabled and exam.duration:
        now = timezone.now()
        end_time = attempt.start_time + timezone.timedelta(minutes=exam.duration)
        remaining_seconds = max(0, int((end_time - now).total_seconds()))
    else:
        remaining_seconds = 0  # 0 = unlimited / no timer

    # Get questions from session (maintains order)
    session_key = f'exam_{exam.id}_questions'
    
    if session_key not in request.session:
        import random
        exam_question_set = exam.questions.all()
        if exam_question_set.exists():
            questions = list(exam_question_set)
        else:
            questions = list(Question.objects.filter(subject=exam.subject))

        if exam.randomize_questions:
            random.shuffle(questions)
        questions = questions[:exam.total_questions]
        
        # Store question IDs in session
        request.session[session_key] = [q.id for q in questions]
        request.session.modified = True
    else:
        question_ids = request.session[session_key]
        questions = [Question.objects.get(id=qid) for qid in question_ids if Question.objects.filter(id=qid).exists()]

    # Get saved answers for THIS exam - use .values() to avoid stale cache
    saved_qs = StudentAnswer.objects.filter(student=request.user, exam=exam).values('question_id', 'selected_answer')
    saved_answers_dict = {a['question_id']: a['selected_answer'] for a in saved_qs}
    
    if request.method == 'POST':
        # BETTER FIX: Direct query per question to avoid dictionary caching issues
        score = 0
        for q in questions:
            ans = StudentAnswer.objects.filter(
                student=request.user,
                exam=exam,
                question=q
            ).values_list('selected_answer', flat=True).first()
            
            if ans and ans.strip().upper() == q.correct_answer.strip().upper():
                score += 1

# Recalculate risk at submit — same weighted-total formula as log_event
        # so the student's final result is consistent with live monitoring.
        logs = IntegrityLog.objects.filter(user=request.user, exam=exam)
        total_penalty = logs_to_total(logs)
        if total_penalty >= 25:
            risk_level = 'CRITICAL'
        elif total_penalty >= 15:
            risk_level = 'HIGH'
        elif total_penalty >= 5:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'

        # Calculate non-linear integrity score to match live updates
        if total_penalty <= 4:
            integrity_score = 100 - (total_penalty * 2.5)
        elif total_penalty <= 14:
            integrity_score = 89 - ((19/9) * (total_penalty - 5))
        elif total_penalty <= 24:
            integrity_score = 69 - ((19/9) * (total_penalty - 15))
        else:
            # For 25 and above, we want to go from 49 down to 0 as penalty goes from 25 to 100
            capped_penalty = min(total_penalty, 100)
            integrity_score = 49 - ((49/75) * (capped_penalty - 25))
        
        # Clamp between 0 and 100 and round to nearest integer
        integrity_score = max(0, min(100, round(integrity_score)))

        # Calculate percentage score
        percentage_score = round((score / len(questions)) * 100, 2) if questions else 0.0

        attempt.status = 'completed'
        attempt.score = score
        attempt.total_questions = len(questions)
        attempt.percentage_score = percentage_score
        attempt.integrity_score = integrity_score
        attempt.risk_level = risk_level
        attempt.end_time = timezone.now()
        attempt.save()
        IntegrityLog.objects.filter(user=request.user, exam=exam).update(is_reviewed=True)

        result = ExamResult.objects.create(
            student=request.user,
            exam=exam,
            score=score,
            total_questions=len(questions),
            percentage_score=percentage_score,
            integrity_score=integrity_score,
            risk_level=risk_level
        )

        return render(request, 'result.html', {
            'score': score,
            'total': len(questions),
            'percentage_score': percentage_score,
            'result': result,
            'attempt': attempt
        })

    current_index = int(request.GET.get('q', 1))
    current_index = max(1, min(current_index, len(questions)))
    current_question = questions[current_index - 1]
    
    has_prev = current_index > 1
    has_next = current_index < len(questions)
    prev_index = current_index - 1
    next_index = current_index + 1
    
    answered_count = len(saved_answers_dict)
    progress_percent = int((answered_count / len(questions)) * 100) if questions else 0
    
    return render(request, 'start_exam.html', {
        'exam': exam,
        'questions': questions,
        'current_question': current_question,
        'current_index': current_index,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_index': prev_index,
        'next_index': next_index,
        'duration_seconds': remaining_seconds,
        'duration_enabled': exam.duration_enabled,
        'saved_answers': saved_answers_dict,
        'answered_count': answered_count,
        'progress_percent': progress_percent
    })

@login_required
def save_answer(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        question_id = request.POST.get('question_id')
        selected = request.POST.get('selected')
        exam_id = request.POST.get('exam_id')

        StudentAnswer.objects.update_or_create(
            student=request.user,
            exam_id=exam_id,
            question_id=question_id,
            defaults={'selected_answer': selected}
        )
        return JsonResponse({'status': 'saved'})
    return JsonResponse({'status': 'error'}, status=400)


# =========================
# STUDENT RESULTS
# =========================

@login_required
@student_required
def my_results(request):
    profile = Profile.objects.get(user=request.user)

    if profile.role != 'student':
        return redirect('home')

    attempts = ExamAttempt.objects.filter(
        student=request.user
    ).select_related(
        'exam',
        'exam__subject',
        'exam__subject__instructor',
        'student'
    ).order_by('-start_time')

    result_map = {
        r.exam_id: r.id
        for r in ExamResult.objects.filter(
            student=request.user,
            exam_id__in=[a.exam_id for a in attempts]
        )
    }

    for a in attempts:
        a.result_id = result_map.get(a.exam_id)

    return render(request, 'my_results.html', {
        'results': attempts,
    })


# =========================
# INSTRUCTOR RESULTS
# =========================

@login_required
@instructor_required
def instructor_results(request):
    subject_ids = Subject.objects.filter(instructor=request.user).values_list('id', flat=True)
    
    exams = Exam.objects.filter(subject__instructor=request.user, is_archived=False)
    
    exam_id = request.GET.get('exam')
    
    results = ExamAttempt.objects.select_related(
        'student',
        'exam',
        'exam__subject'
    ).filter(exam__subject__id__in=subject_ids)
    
    if exam_id:
        results = results.filter(exam_id=exam_id)
    
    results = results.order_by('-start_time')

    violation_subquery = IntegrityLog.objects.filter(
        user=OuterRef('student'),
        exam=OuterRef('exam')
    ).values('user').annotate(c=Count('id')).values('c')
    results = results.annotate(violation_count=Subquery(violation_subquery, output_field=IntegerField()))

    return render(request, 'instructor_results.html', {
        'results': results,
        'exams': exams,
        'selected_exam_id': int(exam_id) if exam_id else None,
    })

@login_required
@instructor_required
def export_results_csv(request):
    profile = Profile.objects.get(user=request.user)

    if profile.role != 'instructor':
        return redirect('home')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="exam_integrity_report.csv"'

    writer = csv.writer(response)

    writer.writerow(['Student', 'Exam', 'Score', 'Percentage', 'Integrity Score', 'Risk Level', 'Date Submitted'])

    exam_id = request.GET.get('exam')
    subject_ids = Subject.objects.filter(instructor=request.user).values_list('id', flat=True)
    all_results = ExamResult.objects.filter(exam__subject__id__in=subject_ids).order_by('-submitted_at')
    if exam_id:
        all_results = all_results.filter(exam_id=exam_id)

    seen = set()
    results = []
    for r in all_results:
        key = (r.student_id, r.exam_id)
        if key not in seen:
            seen.add(key)
            results.append(r)

    for r in results:
        writer.writerow([
            r.student.username,
            r.exam.title,
            f"{r.score}/{r.total_questions}",
            f"{r.percentage_score}%",
            r.integrity_score,
            r.risk_level,
            r.submitted_at.strftime("%Y-%m-%d %I:%M %p")
        ])

    return response


@login_required
@instructor_required
def export_results_pdf(request):
    profile = Profile.objects.get(user=request.user)

    if profile.role != 'instructor':
        return redirect('home')

    exam_id = request.GET.get('exam')
    subject_ids = Subject.objects.filter(instructor=request.user).values_list('id', flat=True)
    all_results = ExamResult.objects.filter(exam__subject__id__in=subject_ids).order_by('-submitted_at')
    if exam_id:
        all_results = all_results.filter(exam_id=exam_id)

    seen = set()
    results = []
    for r in all_results:
        key = (r.student_id, r.exam_id)
        if key not in seen:
            seen.add(key)
            results.append(r)

    # Activate the instructor's timezone for proper time display
    user_tz = pytz.timezone(profile.timezone)
    timezone.activate(user_tz)

    html = render_to_string('pdf_template.html', {'results': results})

    return HttpResponse(html)


# =========================
# INSTRUCTOR ANALYTICS
# =========================

@login_required
@instructor_required
def analytics_dashboard(request):
    profile = Profile.objects.get(user=request.user)

    if profile.role != 'instructor':
        return redirect('home')

    exams = Exam.objects.filter(subject__instructor=request.user, is_archived=False).order_by('title')

    # Prefetch current attempts + latest integrity state for each exam
    now = timezone.now()
    monitor_data = []
    total_in_progress = 0
    low_count = 0
    medium_count = 0
    high_count = 0
    critical_count = 0

    _event_types = dict(IntegrityLog.EVENT_TYPES)  # key → human
    _event_types.pop('paste_attempt', None)

    for exam in exams:
        active_attempts = (
            ExamAttempt.objects
            .filter(exam=exam, status='in_progress')
            .select_related('student')
            .order_by('-start_time')
        )
        if not active_attempts.exists():
            continue

        session = []
        for attempt in active_attempts:
            total_q = exam.total_questions
            answered = StudentAnswer.objects.filter(student=attempt.student, exam=exam).count()
            elapsed_min = int((now - attempt.start_time).total_seconds() / 60)

            # Aggregate per-violation-type breakdown for this student + exam
            log_qs = IntegrityLog.objects.filter(
                user=attempt.student, exam=exam
            )
            violations_total = log_qs.count()
            violations = {
                key: log_qs.filter(event_type=key).count()
                for key in _event_types
            }

            # Calculate integrity score and risk level for analytics display
            total_penalty = logs_to_total(log_qs)
            if total_penalty >= 25:
                risk_level = 'CRITICAL'
            elif total_penalty >= 15:
                risk_level = 'HIGH'
            elif total_penalty >= 5:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'LOW'

            if total_penalty <= 4:
                integrity_score = 100 - (total_penalty * 2.5)
            elif total_penalty <= 14:
                integrity_score = 89 - ((19/9) * (total_penalty - 5))
            elif total_penalty <= 24:
                integrity_score = 69 - ((19/9) * (total_penalty - 15))
            else:
                capped_penalty = min(total_penalty, 100)
                integrity_score = 49 - ((49/75) * (capped_penalty - 25))
            integrity_score = max(0, min(100, round(integrity_score)))

            session.append({
                'student': attempt.student,
                'attempt': attempt,
                'answered': answered,
                'total_questions': total_q,
                'progress_pct': int((answered / total_q) * 100) if total_q else 0,
                'integrity_score': integrity_score,
                'risk_level': risk_level,
                'elapsed': elapsed_min,
                'exam_title': exam.title,
                'violations': violations,
                'violations_total': violations_total,
            })
            if risk_level == 'LOW':
                low_count += 1
            elif risk_level == 'MEDIUM':
                medium_count += 1
            elif risk_level == 'HIGH':
                high_count += 1
            elif risk_level == 'CRITICAL':
                critical_count += 1

        monitor_data.append({
            'exam': exam,
            'students': session,
            'live_count': len(session),
        })
        total_in_progress += len(session)

    return render(request, 'analytics.html', {
        'monitor_data': monitor_data,
        'total_exams': exams.count(),
        'total_in_progress': total_in_progress,
        'low_count': low_count,
        'medium_count': medium_count,
        'high_count': high_count,
        'critical_count': critical_count,
        'event_types': _event_types,
        'exams': exams,
    })


# =========================
# INTEGRITY LOGGING
# =========================

@login_required
@instructor_required
def mark_reviewed(request, log_id):
    log = IntegrityLog.objects.get(id=log_id)
    
    if log.exam.subject.instructor == request.user:
        log.is_reviewed = True
        log.save()
        messages.success(request, "Violation marked as reviewed.")
    
    return redirect(request.META.get('HTTP_REFERER', 'instructor_results'))

@login_required
def log_event(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        event_type = request.POST.get('event_type')
        exam_id = request.POST.get('exam_id')

        # Server-controlled penalties - behaviorally meaningful thresholds
        # Adjusted for realistic risk patterns:
        # - LOW: Minor isolated actions (1-4 points)
        # - MEDIUM: Repeated or mixed suspicious behavior (5-14)
        # - HIGH: Clear intentional misconduct (15-24)
        # - CRITICAL: Severe/excessive violations (25+)
        penalty_map = {
            'tab_switch': 4,
            'copy_attempt': 6,
            'paste_attempt': 6,
            'right_click': 1,
            'refresh': 10,
            'devtools': 15,
            'escape_key': 4,
        }
        penalty = penalty_map.get(event_type, 3)

        exam = Exam.objects.get(id=exam_id)

        # Security: Check if student is actually assigned to this exam's subject
        is_assigned = SubjectAssignment.objects.filter(
            subject=exam.subject, 
            student=request.user
        ).exists()
        
        if not is_assigned:
            return JsonResponse({'error': 'Unauthorized'}, status=403)

        # Deduplication - prevent spam within 2 seconds
        recent = IntegrityLog.objects.filter(
            user=request.user,
            exam=exam,
            event_type=event_type,
            timestamp__gte=timezone.now() - timezone.timedelta(seconds=1)
        ).exists()

        if not recent:
            IntegrityLog.objects.create(
                user=request.user,
                exam=exam,
                event_type=event_type,
                penalty=penalty
            )

        # Weighted penalty accumulated from all log events so far —
        # each violation type carries its own weight per penalty_map above.
        logs = IntegrityLog.objects.filter(
            user=request.user,
            exam=exam
        )
        total_penalty = logs_to_total(logs)
         
        # ── One source of truth for risk tiers ─────────────────────────────────
        # LOW      : minor isolated actions (e.g. 1-2 right clicks)          1-4
        # MEDIUM   : repeated or mixed behavior (e.g. 2 tab switches)           5-14
        # HIGH     : intentional misconduct (e.g. copy attempts)               15-24
        # CRITICAL : severe/excessive violations (e.g. devtools + multiples)   25+
        # ───────────────────────────────────────────────────────────────────────
        if total_penalty >= 25:
            risk_level = 'CRITICAL'
        elif total_penalty >= 15:
            risk_level = 'HIGH'
        elif total_penalty >= 5:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'

        # Calculate non-linear integrity score
        if total_penalty <= 4:
            integrity_score = 100 - (total_penalty * 2.5)
        elif total_penalty <= 14:
            integrity_score = 89 - ((19/9) * (total_penalty - 5))
        elif total_penalty <= 24:
            integrity_score = 69 - ((19/9) * (total_penalty - 15))
        else:
            # For 25 and above, we want to go from 49 down to 0 as penalty goes from 25 to 100
            capped_penalty = min(total_penalty, 100)
            integrity_score = 49 - ((49/75) * (capped_penalty - 25))
        
        # Clamp between 0 and 100 and round to nearest integer
        integrity_score = max(0, min(100, round(integrity_score)))

        # Update the attempt's integrity score and risk level
        attempt = ExamAttempt.objects.filter(user=request.user, exam=exam, status='in_progress').first()
        if attempt:
            attempt.integrity_score = integrity_score
            attempt.risk_level = risk_level
            attempt.save()

        return JsonResponse({'status': 'logged', 'risk': risk_level})

    return JsonResponse({'status': 'error'}, status=400)

@login_required
@instructor_required
def view_logs(request, user_id):
    student = User.objects.get(id=user_id)
    
    exam_id = request.GET.get('exam')
    
    if exam_id:
        logs = IntegrityLog.objects.filter(user_id=user_id, exam_id=exam_id).order_by('-timestamp')
        exam_result = ExamAttempt.objects.filter(student_id=user_id, exam_id=exam_id).select_related('exam').first()
    else:
        logs = IntegrityLog.objects.filter(user_id=user_id).order_by('-timestamp')
        exam_result = None
    
    violation_count = logs.count()
    
    return render(request, 'view_logs.html', {
        'logs': logs,
        'student': student,
        'exam_result': exam_result,
        'violation_count': violation_count,
        'selected_exam_id': exam_id,
        'student_id': user_id,
    })

@login_required
@instructor_required
def export_student_logs_pdf(request, user_id):
    profile = Profile.objects.get(user=request.user)
    if profile.role != 'instructor':
        return redirect('home')
    
    # Activate the instructor's timezone for proper time display
    import pytz
    from django.utils import timezone
    user_tz = pytz.timezone(profile.timezone)
    timezone.activate(user_tz)
    
    student = User.objects.get(id=user_id)
    exam_id = request.GET.get('exam')
    
    if exam_id:
        logs = IntegrityLog.objects.filter(user_id=user_id, exam_id=exam_id).order_by('-timestamp')
        exam_result = ExamAttempt.objects.filter(student_id=user_id, exam_id=exam_id).select_related('exam').first()
    else:
        logs = IntegrityLog.objects.filter(user_id=user_id).order_by('-timestamp')
        exam_result = None
    
    violation_count = logs.count()
    
    html = render_to_string('student_logs_pdf.html', {
        'logs': logs,
        'student': student,
        'exam_result': exam_result,
        'violation_count': violation_count,
        'generated_date': timezone.now(),
    })
    
    return HttpResponse(html)

@login_required
@instructor_required
def clear_logs(request):
    if request.method == 'POST':
        IntegrityLog.objects.all().delete()
        
        from django.contrib import messages
        messages.success(request, "All integrity logs have been cleared successfully.")

    return redirect('instructor_results')


# =========================
# EXAM MANAGEMENT - ARCHIVE/RESTORE
# =========================

@login_required
@instructor_required
def archive_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    
    if exam.subject.instructor != request.user:
        return redirect('instructor_dashboard')
    
    exam.is_archived = True
    exam.save()
    messages.success(request, f"Exam '{exam.title}' has been archived.")
    return redirect('instructor_dashboard')

@login_required
@instructor_required
def restore_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    
    if exam.subject.instructor != request.user:
        return redirect('instructor_dashboard')
    
    exam.is_archived = False
    exam.save()
    messages.success(request, f"Exam '{exam.title}' has been restored.")
    return redirect('archived_exams')

@login_required
@instructor_required
def delete_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    
    if exam.subject.instructor != request.user:
        return redirect('instructor_dashboard')
    
    exam_title = exam.title
    exam.delete()
    messages.success(request, f"Exam '{exam_title}' has been deleted.")
    return redirect('archived_exams')

@login_required
@instructor_required
def archived_exams(request):
    exams = Exam.objects.filter(subject__instructor=request.user, is_archived=True)
    return render(request, 'archived_exams.html', {'exams': exams})
