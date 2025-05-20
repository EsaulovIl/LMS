import os
import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from django.contrib.auth import get_user_model
from django.db import connection

from accounts.models import StudentGroup, User
from utils.yadisk import get_yadisk_download_link


def get_student_mentor(user_id):
    """
    Возвращает User-объект ментора для данного студента через ORM,
    без прямых SQL-запросов к таблицам.
    """
    User = get_user_model()
    grp = (
        StudentGroup.objects
        .filter(students__id=user_id)
        .select_related('mentor')
        .first()
    )
    return grp.mentor if grp else None


def upload_file_to_yadisk(
        file_obj,
        student_id: int,
        assignment_type: str,
        assignment_id: int,
        exercise_id: int,
        mentor: bool = False,
        mentor_id: int = None
) -> tuple[str, str]:
    """
    Загружает файл на Яндекс.Диск и возвращает (disk_path, content_url).

    Путь строится как:
      /LMS/student_{student_id}/{assignment_type}_{assignment_id}/exercise_{exercise_id}
      и если mentor=True:
      /LMS/.../exercise_{...}/mentor_{mentor_id}
    затем имя файла без пробелов.

    1) Создаёт директории по сегментам.
    2) Удаляет старый файл (игнорирует 404).
    3) Запрашивает upload-href и PUT-ит файл.
    4) Получает прямую download-ссылку через API.
    """
    token = getattr(settings, 'YANDEX_DISK_TOKEN', None)
    if not token:
        raise ImproperlyConfigured("YANDEX_DISK_TOKEN не задан в settings")

    headers = {"Authorization": f"OAuth {token}"}

    # Подготовка безопасного имени и базового каталога
    safe_name = file_obj.name.replace(' ', '_')
    parts = [
        "LMS",
        f"student_{student_id}",
        f"{assignment_type}_{assignment_id}",
        f"exercise_{exercise_id}"
    ]
    if mentor:
        if not mentor_id:
            raise ValueError("для mentor=True нужно передать mentor_id")
        parts.append(f"mentor_{mentor_id}")

    # Собираем полный путь
    disk_dir = "/" + "/".join(parts)
    disk_path = f"{disk_dir}/{safe_name}"

    # 1) Создаём каждую папку поочерёдно
    build = ""
    for part in parts:
        build += "/" + part
        resp = requests.put(
            "https://cloud-api.yandex.net/v1/disk/resources",
            headers=headers,
            params={"path": build}
        )
        # 201 — создано; 409 — уже есть; иначе — ошибка
        if resp.status_code not in (201, 409):
            resp.raise_for_status()

    # 2) Удаляем предыдущий файл, если есть
    del_resp = requests.delete(
        "https://cloud-api.yandex.net/v1/disk/resources",
        headers=headers,
        params={"path": disk_path, "permanently": "true"}
    )
    if del_resp.status_code not in (204, 404):
        del_resp.raise_for_status()

    # 3) Запрашиваем href для загрузки
    upload_req = requests.get(
        "https://cloud-api.yandex.net/v1/disk/resources/upload",
        headers=headers,
        params={"path": disk_path}
    )
    upload_req.raise_for_status()
    href = upload_req.json().get("href")
    if not href:
        raise IOError("Yandex.Disk не вернул href для загрузки")

    # 4) PUT-им содержимое
    put_resp = requests.put(href, data=file_obj.read())
    put_resp.raise_for_status()

    # 5) Получаем ссылку на скачивание
    content_url = get_yadisk_download_link(disk_path)

    return disk_path, content_url
