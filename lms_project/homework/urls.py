# apps/homework/urls.py
from django.urls import path
from . import views

app_name = 'homework'

urlpatterns = [
    path('<int:pk>/', views.detail, name='detail'),
]
