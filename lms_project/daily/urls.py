from django.urls import path
from .views import daily_submit

app_name = 'daily'

urlpatterns = [
    path('submit/', daily_submit, name='submit'),
]
