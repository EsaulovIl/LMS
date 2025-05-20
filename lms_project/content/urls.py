from django.urls import path
from .views import save_video_progress

app_name = 'content'

urlpatterns = [
    path('videos/<int:video_id>/progress/', save_video_progress, name='video_progress'),
]
