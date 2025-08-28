# services/download_service.py
import yt_dlp
import tempfile
import os
import shutil
import logging
from typing import Optional, Dict

logger = logging.getLogger("smartx_bot.download_service")

YTDL_OPTS = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'ignoreerrors': True,
    'restrictfilenames': True,
}

def download_video(url: str, max_filesize_bytes: Optional[int] = None) -> Dict:
    """
    Download video using yt-dlp into temp dir.
    Returns dict: {status, filepath, info, error}
    Caller must cleanup file path.
    """
    tmpdir = tempfile.mkdtemp(prefix="smartxdl_")
    opts = YTDL_OPTS.copy()
    opts['outtmpl'] = os.path.join(tmpdir, "%(id)s.%(ext)s")
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                return {"status": "error", "error": "No info extracted"}
            # determine filename
            filename = ydl.prepare_filename(info)
            # optionally check filesize (if requested)
            if max_filesize_bytes and os.path.exists(filename):
                if os.path.getsize(filename) > max_filesize_bytes:
                    # cleanup and return error
                    shutil.rmtree(tmpdir, ignore_errors=True)
                    return {"status": "error", "error": "File too large"}
            return {"status": "success", "filepath": filename, "info": info, "tmpdir": tmpdir}
    except Exception as e:
        logger.exception("download_video fail: %s", e)
        shutil.rmtree(tmpdir, ignore_errors=True)
        return {"status": "error", "error": str(e)}
