# onboarding/urls.py

from django.urls import path
from .views import survey_page, quiz_welcome, quiz_start, quiz_question, quiz_finish

app_name = 'onboarding'
urlpatterns = [
    # Анкетирование
    path('survey/', survey_page, name='survey_page'),
    # Тестирование
    path('quiz/welcome/', quiz_welcome, name='quiz_welcome'),
    path('quiz/start/', quiz_start, name='quiz_start'),
    path('quiz/question/<int:step>/', quiz_question, name='quiz_question'),
    path('quiz/finish/', quiz_finish, name='quiz_finish'),
]
