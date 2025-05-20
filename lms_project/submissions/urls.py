from django.urls import path
from .views import solve_exercise, view_solution

app_name = 'submissions'

urlpatterns = [
    path(
        'solve/<int:assignment_id>/<int:exercise_id>/',
        solve_exercise,
        name='solve'
    ),
    path('solution/<int:assignment_id>/<int:exercise_id>/',
         view_solution, name='solution'),
]
