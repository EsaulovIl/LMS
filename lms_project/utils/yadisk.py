import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def get_yadisk_download_link(disk_path: str) -> str:
    api_url = "https://cloud-api.yandex.net/v1/disk/resources/download"
    headers = {"Authorization": f"OAuth {settings.YANDEX_DISK_TOKEN}"}
    params = {"path": disk_path}

    logger.debug(f"[YDisk] GET {api_url} params={params}")
    resp = requests.get(api_url, headers=headers, params=params)
    logger.debug(f"[YDisk] response {resp.status_code}: {resp.text}")

    resp.raise_for_status()
    href = resp.json().get("href")
    logger.debug(f"[YDisk] download href: {href}")
    return href
