from django.contrib import admin
from django.urls import path
from exam_system import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # AUTH
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # MAIN
    path('', views.home, name='home'),
    path('profile/', views.profile, name='profile'),
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('subjects/', views.subjects, name='subjects'),
    path('subjects/<int:subject_id>/', views.manage_subject, name='manage_subject'),
    path('my-subjects/', views.student_subjects, name='student_subjects'),
    path('available-exams/', views.available_exams, name='available_exams'),
    path('already-taken/', views.already_taken, name='already_taken'),
    path('instructor/', views.instructor_dashboard, name='instructor_dashboard'),
    path('create-subject/', views.create_subject, name='create_subject'),
    path('edit-subject/<int:subject_id>/', views.edit_subject, name='edit_subject'),
    path('delete-subject/<int:subject_id>/', views.delete_subject, name='delete_subject'),
    path('archive-subject/<int:subject_id>/', views.archive_subject, name='archive_subject'),
    path('restore-subject/<int:subject_id>/', views.restore_subject, name='restore_subject'),
    path('archived-subject/<int:subject_id>/', views.archived_subject, name='archived_subject'),
    path('add-question/', views.add_question, name='add_question'),
    path('question-bank/', views.question_bank, name='question_bank'),
    path('delete-question/<int:question_id>/', views.delete_question, name='delete_question'),
    path('edit-question/<int:question_id>/', views.edit_question, name='edit_question'),
    path('add-question-to-exam/<int:exam_id>/<int:question_id>/', views.add_question_to_exam, name='add_question_to_exam'),
    path('remove-question-from-exam/<int:exam_id>/<int:question_id>/', views.remove_question_from_exam, name='remove_question_from_exam'),
    path('add-questions-to-exam/<int:exam_id>/', views.add_questions_to_exam, name='add_questions_to_exam'),
    path('create-exam/', views.create_exam, name='create_exam'),
    path('manage-exam/<int:exam_id>/', views.manage_exam, name='manage_exam'),
    path('update-exam/<int:exam_id>/', views.update_exam, name='update_exam'),
    path('assign-students/', views.assign_students, name='assign_students'),
    path('remove-student/<int:assignment_id>/', views.remove_student, name='remove_student'),
    path('exam-guidelines/<int:exam_id>/', views.exam_guidelines, name='exam_guidelines'),
    path('start-exam/<int:exam_id>/', views.start_exam, name='start_exam'),
    path('log-event/', views.log_event, name='log_event'),
    path('view-logs/<int:user_id>/', views.view_logs, name='view_logs'),
    path('export-student-logs-pdf/<int:user_id>/', views.export_student_logs_pdf, name='export_student_logs_pdf'),
    path('mark-reviewed/<int:log_id>/', views.mark_reviewed, name='mark_reviewed'),
    path('clear-logs/', views.clear_logs, name='clear_logs'),
    path('save-answer/', views.save_answer, name='save_answer'),
    path('my-results/', views.my_results, name='my_results'),
    path('instructor-results/', views.instructor_results, name='instructor_results'),
    path('export-csv/', views.export_results_csv, name='export_csv'),
    path('export-pdf/', views.export_results_pdf, name='export_pdf'),
    path('analytics/', views.analytics_dashboard, name='analytics'),
    path('archive-exam/<int:exam_id>/', views.archive_exam, name='archive_exam'),
    path('restore-exam/<int:exam_id>/', views.restore_exam, name='restore_exam'),
    path('delete-exam/<int:exam_id>/', views.delete_exam, name='delete_exam'),
    path('duplicate-exam/<int:exam_id>/', views.duplicate_exam, name='duplicate_exam'),
    path('toggle-exam/<int:exam_id>/', views.toggle_exam, name='toggle_exam'),
    path('archived-exams/', views.archived_exams, name='archived_exams'),
    path('certificate/<int:result_id>/', views.certificate, name='certificate'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
