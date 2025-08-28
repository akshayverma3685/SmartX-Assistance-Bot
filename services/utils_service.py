# services/utils_service.py
import qrcode
from io import BytesIO
from PIL import Image
import requests
import logging

logger = logging.getLogger("smartx_bot.utils_service")

def generate_qr(text: str) -> BytesIO:
    img = qrcode.make(text)
    bio = BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio

def shorten_url(url: str) -> str:
    try:
        # using tinyurl simple API
        r = requests.get(f"http://tinyurl.com/api-create.php?url={url}", timeout=10)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        logger.debug("TinyURL failed: %s", e)
    return url
