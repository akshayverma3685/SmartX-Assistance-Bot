# web/logs_api.py
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional, AsyncIterator
import os
from pathlib import Path
import asyncio
import aiofiles
import config
from core import security

app = FastAPI(title="SmartX Logs API")

LOG_DIR = Path(getattr(config, "LOG_DIR", "logs"))
KNOWN = {"bot.log", "errors.log", "payments.log", "usage.log"}

def require_api_key(x_api_key: Optional[str] = Header(None)):
    if not x_api_key or not security.is_valid_admin_apikey(x_api_key):
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/logs/list")
async def list_logs(x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    out = []
    for name in KNOWN:
        p = LOG_DIR / name
        if p.exists():
            out.append({"name": name, "size": p.stat().st_size, "path": str(p)})
    return JSONResponse(out)

@app.get("/logs/tail")
async def tail_log(file: str, lines: int = 200, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    if file not in KNOWN:
        raise HTTPException(status_code=400, detail="Unknown file")
    path = LOG_DIR / file
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # read last N lines efficiently by reading blocks from end
    async def iter_tail() -> AsyncIterator[str]:
        import os
        block_size = 4096
        file_size = os.path.getsize(path)
        with open(path, "rb") as fh:
            if file_size == 0:
                return
            blocks = []
            remain = file_size
            while remain > 0 and len(blocks) < lines:
                to_read = min(block_size, remain)
                fh.seek(remain - to_read)
                data = fh.read(to_read)
                blocks.insert(0, data)
                remain -= to_read
                # break early if we have enough newlines
                if b"\n" in b"".join(blocks) and len(b"".join(blocks).splitlines()) >= lines:
                    break
            data = b"".join(blocks).decode("utf-8", errors="replace").splitlines()[-lines:]
            for line in data:
                yield line + "\n"

    return StreamingResponse(iter_tail(), media_type="text/plain")

@app.get("/logs/page")
async def page_log(file: str, page: int = 1, per_page: int = 200, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    if file not in KNOWN:
        raise HTTPException(status_code=400, detail="Unknown file")
    path = LOG_DIR / file
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    start = (page - 1) * per_page
    async def iter_page():
        i = 0
        async with aiofiles.open(path, mode="r", encoding="utf-8", errors="replace") as fh:
            async for line in fh:
                if i >= start and i < start + per_page:
                    yield line
                i += 1
                if i >= start + per_page:
                    break
    return StreamingResponse(iter_page(), media_type="text/plain")

@app.get("/logs/stream")
async def stream_log(file: str, x_api_key: Optional[str] = Header(None)):
    """
    Long-poll streaming (simple SSE-like streaming).
    NOTE: This is a basic implementation suitable behind a reverse proxy. Not super-efficient for high load.
    """
    require_api_key(x_api_key)
    if file not in KNOWN:
        raise HTTPException(status_code=400, detail="Unknown file")
    path = LOG_DIR / file
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    async def event_stream():
        # open and seek to end
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            fh.seek(0, os.SEEK_END)
            try:
                while True:
                    line = fh.readline()
                    if line:
                        yield line
                    else:
                        await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                return

    return StreamingResponse(event_stream(), media_type="text/plain")
