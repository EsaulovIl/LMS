from django.urls import path
from .views import home_view, calendar_view, course_view, course_block_themes, theme_content

app_name = 'planning'

urlpatterns = [
    path('', home_view, name='home'),
    path('calendar/', calendar_view, name='calendar'),
    path('course/', course_view, name='course'),
    path(
        'course/<int:section_id>/themes/',
        course_block_themes,
        name='course_block_themes'
    ),
    path(
        'course/<int:section_id>/themes/<int:theme_id>/content/',
        theme_content,
        name='theme_content'
    ),
]
