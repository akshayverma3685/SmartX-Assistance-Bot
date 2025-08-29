"""
admin_panel.__init__

Package bootstrap for SmartX Assistance Admin Panel.

Provides:
- package-level configuration
- logger integration
- FastAPI dependency 'admin_required' to protect admin endpoints (x-api-key or session)
- helper 'create_admin_app' to assemble FastAPI app by auto-including routers from admin modules
- common exports used across admin modules

Design goals:
- Minimal side-effects on import
- Safe defaults (read config from environment or global config)
- Ready for production (logging, secrets handling)
"""

from __future__ import annotations

import os
import logging
from typing import Optional, Callable, Iterable, List

# Expose package version
ADMIN_PANEL_VERSION = os.getenv("ADMIN_PANEL_VERSION", "1.0.0")

# Configurable env variables (can be set via .env or deployment)
ADMIN_API_BASE_URL = os.getenv("ADMIN_API_BASE_URL", os.getenv("ADMIN_API_BASE_URL", "http://adminapi:80"))
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", None)
ADMIN_PANEL_SECRET = os.getenv("ADMIN_PANEL_SECRET", os.getenv("ADMIN_PANEL_SECRET", "change-me"))
ADMIN_PANEL_TITLE = os.getenv("ADMIN_PANEL_TITLE", "SmartX Admin Panel")

# Logging: use core.logs if available, otherwise fallback
try:
    # prefer structured logs manager if project provides it
    from core.logs import get_logs_manager, log_info, log_error  # type: ignore
    _logs = get_logs_manager()
    _logger = logging.getLogger("admin_panel")
    _logger.setLevel(logging.INFO)
except Exception:
    _logger = logging.getLogger("admin_panel")
    if not _logger.handlers:
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s : %(message)s"))
        _logger.addHandler(ch)
    _logger.setLevel(logging.INFO)


# -------------------------
# Helper accessors
# -------------------------
def get_admin_api_key() -> Optional[str]:
    """
    Return Admin API key from environment/config.
    Keep as single accessor so tests can monkeypatch if needed.
    """
    return ADMIN_API_KEY


# -------------------------
# FastAPI dependency for admin protection
# -------------------------
# Import here to avoid forcing FastAPI dependency on module import
def admin_required_header_checker():
    """
    Return a dependency function that can be used with FastAPI's Depends
    to require an 'x-api-key' or session to access admin endpoints.
    Usage:
        from admin_panel import admin_required
        @app.get("/secret", dependencies=[Depends(admin_required)])
    """
    from fastapi import Request, HTTPException

    def _dep(request: Request):
        # 1) first check header x-api-key
        provided = request.headers.get("x-api-key") or request.headers.get("X-API-KEY")
        if provided and ADMIN_API_KEY:
            # use timing-safe compare
            try:
                import hmac
                if hmac.compare_digest(str(provided), str(ADMIN_API_KEY)):
                    return True
            except Exception:
                # fallback simple compare
                if provided == ADMIN_API_KEY:
                    return True
        # 2) next, check signed session cookie (if your main admin uses sessions)
        # We keep this generic: if session exists with 'api_key' we accept
        try:
            sess_key = request.session.get("api_key") if hasattr(request, "session") else None
            if sess_key and ADMIN_API_KEY and str(sess_key) == str(ADMIN_API_KEY):
                return True
        except Exception:
            pass
        # 3) not authorized
        raise HTTPException(status_code=403, detail="Admin authorization required")

    return _dep


# Single instance for imports
admin_required = admin_required_header_checker()


# -------------------------
# Create FastAPI app helper
# -------------------------
def create_admin_app(include_modules: Optional[Iterable[str]] = None, title: Optional[str] = None):
    """
    Create a FastAPI app pre-configured for the admin panel.
    - include_modules: iterable of module paths (strings) to import and auto-include routers from.
      Each module is expected to expose a FastAPI APIRouter as `router` (optional).
      Example: ['admin_panel.dashboard', 'admin_panel.user_manager']
    - title: override panel title

    Returns the FastAPI app instance.
    """
    from fastapi import FastAPI
    from fastapi.middleware.sessions import SessionMiddleware

    app_title = title or ADMIN_PANEL_TITLE
    app = FastAPI(title=app_title)

    # Session middleware (signed cookie) - used by some admin pages
    # SECRET should be long & random in production
    secret = ADMIN_PANEL_SECRET or "change-me"
    app.add_middleware(SessionMiddleware, secret_key=secret, session_cookie="smartx_admin_session", https_only=False)

    # auto-include routers if modules provided
    mods = list(include_modules) if include_modules else []
    # Default modules which commonly export router objects
    if not mods:
        mods = [
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
            if router is not None:
                app.include_router(router, prefix=f"/{m.split('.')[-1]}")
                included.append(m)
                _logger.info("Included admin router: %s", m)
        except Exception as e:
            _logger.debug("Module %s not included (no router or import error): %s", m, e)

    # add a small root route if not present
    @app.get("/", tags=["admin"])
    async def root():
        return {"ok": True, "panel": app_title, "version": ADMIN_PANEL_VERSION, "routes_included": included}

    return app


# -------------------------
# Utility: register_cli_commands
# -------------------------
def register_cli_commands(cli_app):
    """
    Optional helper to register admin-panel CLI subcommands into a main CLI app (e.g., Typer or Click).
    This attempts to import modules like user_management, stats_dashboard etc. and add them as commands.
    """
    try:
        import importlib
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
                m = importlib.import_module(mod_name)
                # many admin scripts expose a 'cli' Typer/Click app or 'main' function
                if hasattr(m, "cli") and hasattr(cli_app, "add_typer"):
                    cli_app.add_typer(getattr(m, "cli"), name=mod_name.split(".")[-1])
                elif hasattr(m, "main") and hasattr(cli_app, "command"):
                    # wrap simple function
                    cli_app.command(name=mod_name.split(".")[-1])(getattr(m, "main"))
            except Exception:
                _logger.debug("Failed to register CLI from %s", mod_name)
    except Exception:
        _logger.debug("register_cli_commands helper failed")


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
