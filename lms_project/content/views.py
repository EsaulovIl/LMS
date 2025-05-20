import logging

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST

from .models import VideoLesson, VideoProgress

logger = logging.getLogger(__name__)


@require_POST
@login_required
def save_video_progress(request, video_id):
    video = get_object_or_404(VideoLesson, pk=video_id)

    # Распарсим JSON
    try:
        payload = json.loads(request.body)
        pct = float(payload.get('percent', 0))
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        logger.error("Invalid JSON: %s", e)
        return HttpResponseBadRequest("Invalid JSON")

    pct = max(0.0, min(100.0, pct))

    # Берём или создаём запись
    vp, created = VideoProgress.objects.get_or_create(
        student=request.user,
        video=video,
        defaults={'watched_percent': 0.0, 'viewed': False}
    )

    updated = False

    if not vp.viewed:
        # первый просмотр: обновляем только при росте pct
        if pct > vp.watched_percent:
            vp.watched_percent = pct
            updated = True
        # если достигли 100% — ставим флаг viewed
        if pct >= 100.0:
            vp.viewed = True
            updated = True
    else:
        # повторный просмотр: всегда обновляем таймкод
        if pct != vp.watched_percent:
            vp.watched_percent = pct
            updated = True

    if updated:
        vp.save(update_fields=['watched_percent', 'viewed', 'last_watched_at'])
        logger.debug(
            "VideoProgress updated (id=%s): watched=%.1f%% viewed=%s",
            vp.id, vp.watched_percent, vp.viewed
        )

    return JsonResponse({
        'status': 'ok',
        'created': created,
        'watched_percent': vp.watched_percent,
        'viewed': vp.viewed,
    })
