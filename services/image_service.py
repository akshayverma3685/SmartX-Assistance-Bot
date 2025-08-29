"""
image_service.py
Service for handling all image-related operations in SmartX Assistance Bot.
Features:
- Download images from Telegram
- Validate and optimize images
- Save locally or to cloud storage
- Return image metadata for DB saving
"""

import os
import io
import logging
from PIL import Image
from typing import Optional, Dict
from aiogram import Bot
from aiogram.types import File

from core.security import generate_secure_filename
from core.cache import cache_result
from logs.bot_logger import get_bot_logger

# Config
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MEDIA_DIR = os.path.join(BASE_DIR, "media", "images")
os.makedirs(MEDIA_DIR, exist_ok=True)

logger = get_bot_logger()

class ImageService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def download_image(self, file_id: str) -> Optional[str]:
        """
        Download an image from Telegram servers and save locally.
        Returns the saved file path or None.
        """
        try:
            tg_file: File = await self.bot.get_file(file_id)
            file_ext = os.path.splitext(tg_file.file_path)[-1] or ".jpg"

            # Generate secure filename
            filename = generate_secure_filename(prefix="img", extension=file_ext)
            file_path = os.path.join(MEDIA_DIR, filename)

            # Download
            await self.bot.download_file(tg_file.file_path, destination=file_path)

            logger.info("Image downloaded",
                        extra={"source": "image_service.download", "meta": {"file_id": file_id, "path": file_path}})
            return file_path
        except Exception as e:
            logger.exception("Failed to download image",
                             extra={"source": "image_service.download", "meta": {"file_id": file_id}})
            return None

    @cache_result(ttl=60)  # cache metadata for 1 min
    def optimize_image(self, file_path: str, max_size: int = 1080) -> Optional[Dict]:
        """
        Optimize image (resize, compress).
        Returns metadata dict.
        """
        try:
            with Image.open(file_path) as img:
                # Convert to RGB (avoid PNG with alpha issues)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                # Resize if too large
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size))

                # Save optimized
                optimized_path = file_path.rsplit(".", 1)[0] + "_opt.jpg"
                img.save(optimized_path, "JPEG", quality=85, optimize=True)

                metadata = {
                    "original_path": file_path,
                    "optimized_path": optimized_path,
                    "width": img.width,
                    "height": img.height,
                    "size_kb": os.path.getsize(optimized_path) // 1024,
                    "mime_type": "image/jpeg"
                }

                logger.info("Image optimized",
                            extra={"source": "image_service.optimize", "meta": metadata})
                return metadata

        except Exception:
            logger.exception("Image optimization failed",
                             extra={"source": "image_service.optimize", "meta": {"path": file_path}})
            return None

    def delete_image(self, file_path: str) -> bool:
        """
        Delete an image file from disk.
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info("Image deleted",
                            extra={"source": "image_service.delete", "meta": {"path": file_path}})
                return True
            return False
        except Exception:
            logger.exception("Failed to delete image",
                             extra={"source": "image_service.delete", "meta": {"path": file_path}})
            return False
