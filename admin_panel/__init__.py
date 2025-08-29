from __future__ import annotations

import logging
from typing import Optional

ADMIN_PANEL_VERSION = os.getenv(
    "ADMIN_PANEL_VERSION",
    "1.0.0"
)
ADMIN_API_BASE_URL = os.getenv(
    "ADMIN_API_BASE_URL",
    "http://adminapi:80"
)
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", None)
ADMIN_PANEL_SECRET = os.getenv(
    "ADMIN_PANEL_SECRET",
    "change-me"
)
ADMIN_PANEL_TITLE = os.getenv(
    "ADMIN_PANEL_TITLE",
    "SmartX Admin Panel"
)

try:
    _logger = logging.getLogger("admin_panel")
    _logger.setLevel(logging.INFO)
except Exception:
    _logger = logging.getLogger("admin_panel")
    if not _logger.handlers:
        ch = logging.StreamHandler()
        ch.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s : %(message)s"
            )
        )
        _logger.addHandler(ch)
    _logger.setLevel(logging.INFO)


def get_admin_api_key() -> Optional[str]:
    """Return Admin API key from environment/config."""
    return ADMIN_API_KEY


def admin_required_header_checker():
    from fastapi import Request, HTTPException
    import hmac

    def _dep(request: Request):
        provided = (
            request.headers.get("x-api-key") or
            request.headers.get("X-API-KEY")
        )
        if provided and ADMIN_API_KEY:
            try:
                if hmac.compare_digest(
                    str(provided),
                    str(ADMIN_API_KEY)
                ):
                    return True
            except Exception:
                if provided == ADMIN_API_KEY:
                    return True

        try:
            sess_key = (
                request.session.get("api_key")
                if hasattr(request, "session") else None
            )
            if sess_key and ADMIN_API_KEY and str(sess_key) == str(
                ADMIN_API_KEY
            ):
                return True
        except Exception:
            pass

        raise HTTPException(
            status_code=403,
            detail="Admin authorization required"
        )

    return _dep


admin_required = admin_required_header_checker()


# -------------------------
# Create FastAPI app helper
# -------------------------
def create_admin_app(
    include_modules: Optional[list[str]] = None,
    title: Optional[str] = None
):
    """
    Create a FastAPI app pre-configured for the admin panel.

    - include_modules: list of module paths to auto-include routers.
    - title: override panel title

    Returns the FastAPI app instance.
    """
    from fastapi import FastAPI
    from fastapi.middleware.sessions import SessionMiddleware

    app_title = title or ADMIN_PANEL_TITLE
    app = FastAPI(title=app_title)

    secret = ADMIN_PANEL_SECRET or "change-me"
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret,
        session_cookie="smartx_admin_session",
        https_only=False
    )

    mods = list(include_modules) if include_modules else [
        "admin_panel.dashboard",
        "admin_panel.user_manager",
        "admin_panel.payment_manager",
        "admin_panel.broadcast",
        "admin_panel.settings_manager",
        "admin_panel.logs_viewer",
        "admin_panel.error_monitor",
        "admin_panel.audit_trail",
        "admin_panel.stats_dashboard",
    ]

    included = []
    for m in mods:
        try:
            mod = __import__(m, fromlist=["router"])
            router = getattr(mod, "router", None)
            if router:
                app.include_router(
                    router,
                    prefix=f"/{m.split('.')[-1]}"
                )
                included.append(m)
                _logger.info("Included admin router: %s", m)
        except Exception as e:
            _logger.debug(
                "Module %s not included (no router or import error): %s",
                m,
                e
            )

    @app.get("/", tags=["admin"])
    async def root():
        return {
            "ok": True,
            "panel": app_title,
            "version": ADMIN_PANEL_VERSION,
            "routes_included": included,
        }

    return app


# -------------------------
# Utility: register_cli_commands
# -------------------------
def register_cli_commands(cli_app):
    """Register admin-panel CLI subcommands into main CLI app."""
    modules = [
        "admin_panel.user_management",
        "admin_panel.payment_logs",
        "admin_panel.logs_viewer",
        "admin_panel.settings_manager",
        "admin_panel.broadcast",
        "admin_panel.stats_dashboard",
    ]
    for mod_name in modules:
        try:
            m = __import__(mod_name, fromlist=["cli", "main"])
            if hasattr(m, "cli") and hasattr(cli_app, "add_typer"):
                cli_app.add_typer(
                    getattr(m, "cli"),
                    name=mod_name.split(".")[-1]
                )
            elif hasattr(m, "main") and hasattr(cli_app, "command"):
                cli_app.command(
                    name=mod_name.split(".")[-1]
                )(getattr(m, "main"))
        except Exception:
            _logger.debug("Failed to register CLI from %s", mod_name)


# -------------------------
# Exports
# -------------------------
__all__ = [
    "ADMIN_PANEL_VERSION",
    "ADMIN_API_BASE_URL",
    "ADMIN_API_KEY",
    "ADMIN_PANEL_SECRET",
    "ADMIN_PANEL_TITLE",
    "get_admin_api_key",
    "admin_required",
    "create_admin_app",
    "register_cli_commands",
]
