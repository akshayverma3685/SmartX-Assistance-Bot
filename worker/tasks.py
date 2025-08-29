# worker/tasks.py
from .celery_app import celery_app
import services.download_service as download_service
import services.s3_service as s3_service
import os
import logging
from core import database

logger = logging.getLogger("smartx_bot.tasks")


@celery_app.task(bind=True)
def download_and_upload(
    self, url: str, user_id: int, max_filesize_bytes: int = None
):
    """
    Downloads the URL, uploads to S3, 
    returns dict with status and url or error.
    This runs in worker. Caller can poll result
    or receive webhook style notification.
    """
    try:
        res = download_service.download_video(url, max_filesize_bytes)
        if res.get("status") != "success":
            return {"status": "error", "error": res.get("error")}
        filepath = res.get("filepath")
        tmpdir = res.get("tmpdir")
        # upload to s3
        object_name = f"{user_id}/{os.path.basename(filepath)}"
        key = s3_service.upload_file(filepath, object_name=object_name)
        if not key:
            return {"status": "error", "error": "S3 upload failed"}
        presigned = s3_service.generate_presigned_url(
            key, expires_in_seconds=24*3600
        )
        # cleanup
        try:
            if tmpdir:
                import shutil
                shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass
        # Optionally: write log to DB
        try:
            db = database.get_mongo_db()
            await_obj = None
            # can't await here (celery task sync) — 
            # use direct motor (blocking) or omit
            # For simplicity, write minimal to DB using motor sync? 
            # We'll skip DB log here.
        except Exception:
            logger.debug("Skipping DB log in task.")
        return {"status": "success", "url": presigned}
    except Exception as e:
        logger.exception("Task exception: %s", e)
        return {"status": "error", "error": str(e)}
