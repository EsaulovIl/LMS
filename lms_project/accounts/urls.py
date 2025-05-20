from django.urls import path, reverse_lazy
from django.contrib.auth.views import LogoutView
from .views import register_view, CustomLoginView, logout_view, welcome_view, profile_view, mark_notifications_read

app_name = 'accounts'

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path('welcome/', welcome_view, name='welcome'),
    path('profile/', profile_view, name='profile'),
    path('notifications/mark_read/', mark_notifications_read, name='notif_mark_read'),
]
