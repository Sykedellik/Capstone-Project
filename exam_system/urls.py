from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("student/dashboard/", views.student_dashboard, name="student_dashboard"),
    path("instructor/dashboard/", views.instructor_dashboard, name="instructor_dashboard"),
]