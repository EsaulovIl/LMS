# apps/mentors/urls.py
from django.urls import path
from .views import (mentor_check_list, mentor_exams_list,
                    mentor_homework_detail, mentor_exam_review)

app_name = 'mentors'

urlpatterns = [
    path('check/', mentor_check_list, name='check'),
    path('check/<int:homework_pk>/<int:exercise_pk>/',mentor_homework_detail,name='check_detail'),
    # список пробников
    path('exams/', mentor_exams_list, name='exams'),
    path('exams/<int:exam_pk>/', mentor_exam_review, name='exam_review'),
]
