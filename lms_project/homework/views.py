# apps/homework/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Max

from .models import Homework
from submissions.models import Submission


@login_required
def detail(request, pk):
    # 1) Берём домашку
    hw = get_object_or_404(
        Homework.objects.select_related('schedule__theme'),
        pk=pk,
        schedule__plan__student=request.user
    )

    # 2) Находим первое упражнение и редиректим туда
    first_ex = hw.exercises.order_by('pk').first()
    if first_ex:
        return redirect('submissions:solve', hw.pk, first_ex.pk)

    # 3) Если упражнений нет — показываем «пустую» страницу
    return render(request, 'homework/detail.html', {
        'homework': hw,
        'exercises': []
    })
