from django.urls import path, include
from accounts.views import welcome_view

from onboarding.views import quiz_finish

urlpatterns = [
    # при заходе на '/', сразу на страницу приветствия
    path('', welcome_view, name='welcome'),

    path('accounts/', include('accounts.urls')),

    path('content/', include('content.urls')),

    path('daily/', include('daily.urls')),

    path('exams/', include('exams.urls')),

    path('homework/', include('homework.urls')),

    path('mentor/', include('mentors.urls')),

    path('onboarding/', include('onboarding.urls')),

    path('onboarding/quiz/finish/', quiz_finish, name='quiz_finish'),

    path('planning/', include('planning.urls')),

    path('practice/', include('practice.urls')),

    path('submissions/', include('submissions.urls'))
]
