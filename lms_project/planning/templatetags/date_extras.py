# apps/planning/templatetags/date_extras.py
from datetime import date, datetime
from django import template
from django.utils import timezone

register = template.Library()

@register.filter
def deadline_color(deadline):
    """
    danger – 0-1 день      (красный)
    warn   – 2-6 дней      (жёлтый)
    ok     – 7 и более     (зелёный)
    """
    if not deadline:
        return "ok"

    today = timezone.localdate()

    # 1. aware/naive datetime  → date
    if isinstance(deadline, datetime):
        deadline = deadline.date()

    # 2. теперь гарантированно date ↔ date
    if not isinstance(deadline, date):
        return "ok"                        # неожиданный тип – по умолчанию «зелёный»

    delta_days = (deadline - today).days

    if delta_days <= 1:
        return "danger"
    elif delta_days < 7:
        return "warn"
    return "ok"
