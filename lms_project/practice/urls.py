from django.urls import path
from . import views

app_name = 'practice'

urlpatterns = [
    # 1) Список разделов с отработками
    path('blocks/', views.blocks_list, name='blocks_list'),

    # 2) Темы в разделе, где есть отработки
    path('blocks/<int:section_id>/topics/', views.block_topics, name='block_topics'),

    # 3) Сами упражнения для отработки по теме
    path('blocks/<int:section_id>/topics/<int:theme_id>/exercises/',
         views.topic_exercises, name='topic_exercises'),
]
