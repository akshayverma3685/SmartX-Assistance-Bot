# services/download_service.py
import yt_dlp
import tempfile
import os
import logging
from typing import Optional
logger = logging.getLogger("smartx_bot.download_service")

YTDL_OPTS = {
    'format': 'bestvideo+bestaudio/best',
    'outtmpl': '%(id)s.%(ext)s',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
}

def download_video(url: str, out_dir: Optional[str] = None) -> dict:
    if out_dir is None:
        out_dir = tempfile.mkdtemp()
    ydl_opts = YTDL_OPTS.copy()
    ydl_opts['outtmpl'] = os.path.join(out_dir, '%(id)s.%(ext)s')
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        return {"status":"success","filepath":filename,"info":info}
    except Exception as e:
        logger.exception("Download failed: %s", e)
        return {"status":"error","error": str(e)}
