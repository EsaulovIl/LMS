from datetime import date
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth.decorators import login_required

from .models import DailyQuizAssignment, DailyQuizOption, DailyQuizTask


@login_required
def daily_submit(request):
    if request.method != 'POST':
        return redirect('planning:home')

    today = date(2025, 5, 8)
    # берём назначение на сегодня
    assignment = get_object_or_404(
        DailyQuizAssignment,
        user=request.user,
        assigned_date=today
    )
    # если уже выполнено — больше не меняем
    if assignment.completed_at:
        return redirect('planning:home')

    # обрабатываем выбор
    opt_id = request.POST.get('option')
    option = get_object_or_404(DailyQuizOption, pk=opt_id, task=assignment.task)

    assignment.selected_option = option
    assignment.is_correct = option.is_correct
    assignment.completed_at = timezone.now()
    assignment.save()

    return redirect('planning:home')
