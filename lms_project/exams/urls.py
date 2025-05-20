from django.urls import path
from . import views

app_name = 'exams'
urlpatterns = [
    path('', views.exam_list, name='list'),
    path('<int:exam_id>/', views.exam_detail, name='detail'),
    path('<int:exam_id>/results/', views.exam_results, name='results'),
    path('<int:exam_id>/finish/', views.finish_exam, name='finish'),
]
