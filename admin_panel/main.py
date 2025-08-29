# admin-panel/main.py
from fastapi import FastAPI, Request, Form, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates
from settings import settings
from utils.security import encode_session, decode_session
from utils.http import api_get, api_post
import httpx

app = FastAPI(title=settings.TITLE)
templates = Jinja2Templates(directory="templates")

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Sessions (sign + encrypt via SECRET_KEY)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie=settings.COOKIE_NAME,
    https_only=settings.COOKIE_SECURE,
    same_site="lax",
    domain=settings.COOKIE_DOMAIN,
)


def get_api_key(request: Request) -> str | None:
    # prefer session-stored key
    sess_key = request.session.get("api_key")
    if sess_key:
        return sess_key
    # fallback env (auto-login)
    return settings.ADMIN_API_KEY


def require_login(request: Request) -> str | None:
    key = get_api_key(request)
    if not key:
        return None
    return key
    

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # If env has ADMIN_API_KEY, auto-login
    env_key = settings.ADMIN_API_KEY
    if env_key:
        request.session["api_key"] = env_key
        return RedirectResponse(
            "/", status_code=status.HTTP_302_FOUND
        )
    return templates.TemplateResponse(
        "login.html", {"request": request, "title": settings.TITLE}
    )


@app.post("/login")
async def login_submit(request: Request, api_key: str = Form(...)):
    # Quick health check with provided key
    try:
        # call /stats to validate
        await api_get("/stats", api_key)
    except Exception:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "title": settings.TITLE,
                "error": "Invalid API key or Admin API unreachable.",
            },
            status_code=401,
        )
    request.session["api_key"] = api_key
    return RedirectResponse(
        "/", status_code=status.HTTP_302_FOUND
    )


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(
        "/login", status_code=status.HTTP_302_FOUND
    )


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    api_key = require_login(request)
    if not api_key:
        return RedirectResponse(
            "/login", status_code=status.HTTP_302_FOUND
        )

    # Fetch stats & health
    stats, health = {}, {}
    error = None
    try:
        stats = await api_get("/stats", api_key)
        async with httpx.AsyncClient(
            base_url=settings.ADMIN_API_BASE_URL, timeout=10
        ) as client:
            r = await client.get("/health")
            r.raise_for_status()
            health = r.json()
    except Exception:
        error = "Admin API error — check connectivity / key."

    ctx = {
        "request": request,
        "title": settings.TITLE,
        "stats": stats,
        "health": health,
        "error": error,
    }
    return templates.TemplateResponse("dashboard.html", ctx)


@app.get("/users/export")
async def users_export(request: Request):
    api_key = require_login(request)
    if not api_key:
        return RedirectResponse(
            "/login", status_code=status.HTTP_302_FOUND
        )
    # Stream CSV directly from Admin API
    async with httpx.AsyncClient(
        base_url=settings.ADMIN_API_BASE_URL, timeout=None
    ) as client:
        r = await client.get(
            "/export/users.csv",
            headers={"x-api-key": api_key}
        )
        r.raise_for_status()
        headers = {
            "Content-Disposition": r.headers.get(
                "content-disposition", "attachment; filename=users.csv"
            )
        }
        return StreamingResponse(
            r.aiter_raw(), media_type="text/csv", headers=headers
        )


@app.get("/broadcast", response_class=HTMLResponse)
async def broadcast_page(request: Request):
    api_key = require_login(request)
    if not api_key:
        return RedirectResponse(
            "/login", status_code=status.HTTP_302_FOUND
        )
    return templates.TemplateResponse(
        "broadcast.html", {"request": request, "title": settings.TITLE}
    )


@app.post("/broadcast")
async def broadcast_send(request: Request, message: str = Form(...)):
    api_key = require_login(request)
    if not api_key:
        return RedirectResponse(
            "/login", status_code=status.HTTP_302_FOUND
        )
    try:
        res = await api_post("/broadcast", api_key, {"message": message})
        notice = (
            "Broadcast scheduled ✅"
            if res.get("status") == "scheduled"
            else "Broadcast request sent."
        )
        return templates.TemplateResponse(
            "broadcast.html",
            {"request": request, "title": settings.TITLE, "notice": notice}
        )
    except Exception:
        return templates.TemplateResponse(
            "broadcast.html",
            {
                "request": request,
                "title": settings.TITLE,
                "error": "Failed to schedule broadcast.",
            },
            status_code=500,
    )
