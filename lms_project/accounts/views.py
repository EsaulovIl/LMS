from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .forms import RegisterForm, CustomAuthenticationForm, ProfileForm
from django.urls import reverse_lazy, reverse
from django.contrib.auth import logout
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth import update_session_auth_hash


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('onboarding:survey_page')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = CustomAuthenticationForm

    # redirect_authenticated_user = True

    def form_invalid(self, form):
        # Добавляем flash-уведомление об ошибке
        messages.error(self.request, "Неверный логин или пароль")
        return super().form_invalid(form)

    def get_success_url(self):
        user = self.request.user
        # если ментор — сразу на /mentor/
        if user.role.name == 'mentor':
            return reverse('mentors:check')
        # иначе — на планирование
        return reverse('planning:home')


def logout_view(request):
    """
    Разлогинивает пользователя и редиректит на страницу логина.
    """
    logout(request)
    return redirect('accounts:login')


def welcome_view(request):
    """
    Публичная страница приветствия для всех посетителей.
    """
    # Если уже залогинен — отправим сразу в личный кабинет
    if request.user.is_authenticated:
        return redirect('planning:home')

    # иначе рендерим шаблон с выбором «Войти / Зарегистрироваться»
    return render(request, 'accounts/welcome.html')


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            user = form.save()
            # Если пароль изменялся — нужно обновить сессию
            if form.cleaned_data.get('new_password'):
                update_session_auth_hash(request, user)
            messages.success(request, "Профиль сохранён")
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)

    notes = request.user.notifications.all()[:5]
    unread_count = request.user.notifications.filter(read_at__isnull=True).count()

    return render(request, 'accounts/profile.html', {
        'form': form,
        'notifications': notes,
        'unread_count': unread_count,
    })


@require_POST
@login_required
def mark_notifications_read(request):
    """
    POST-запросом помечаем все непрочитанные уведомления текущего пользователя как прочитанные.
    """
    unread = request.user.notifications.filter(read_at__isnull=True)
    count = unread.update(read_at=timezone.now())
    return JsonResponse({'marked': count})
