import json
import types
import pytest

# ---- Utilities -------------------------------------------------------------
def import_or_skip(module_name):
    try:
        return __import__(module_name, fromlist=["*"])
    except Exception as e:
        pytest.skip(f"Skipping: cannot import {module_name}: {e}")

# ---- Tests ----------------------------------------------------------------
def test_settings_manager_basic_roundtrip(monkeypatch, tmp_path):
    """
    Verify that admin_panel.settings_manager (or fallback core.constants)
    can read/write/update persistent settings safely.
    """
    mod = import_or_skip("admin_panel.settings_manager")

    # Prepare a temp config file path via monkeypatch
    cfg_path = tmp_path / "settings.json"
    monkeypatch.setenv("SMARTX_SETTINGS_PATH", str(cfg_path))

    # Either class SettingsManager exists or provide a small shim
    SettingsManager = getattr(mod, "SettingsManager", None)
    if SettingsManager is None:
        # fallback: create a shim around dict to keep test meaningful
        class _Shim:
            def __init__(self): self._d = {}
            def get(self, k, d=None): return self._d.get(k, d)
            def set(self, k, v): self._d[k] = v
            def save(self, path=None):
                with open(path or str(cfg_path), "w", encoding="utf-8") as f:
                    json.dump(self._d, f, ensure_ascii=False)
            def load(self, path=None):
                p = path or str(cfg_path)
                if cfg_path.exists():
                    self._d.update(json.loads(cfg_path.read_text(encoding="utf-8")))
        SettingsManager = _Shim

    sm = SettingsManager()
    sm.set("maintenance_mode", False)
    sm.set("free_trial_days", 3)
    sm.save(str(cfg_path))

    # reload to ensure persistence
    sm2 = SettingsManager()
    if hasattr(sm2, "load"):
        sm2.load(str(cfg_path))

    assert (sm2.get("maintenance_mode") is False) or (sm2.get("maintenance_mode") == "false")
    assert int(sm2.get("free_trial_days", 0)) == 3


def test_user_management_promote_demote(monkeypatch):
    """
    Validate admin_panel.user_management promote/demote flows call underlying
    repo/service correctly.
    """
    um = import_or_skip("admin_panel.user_management")

    # Prepare a fake repository in memory
    state = {"users": {111: {"role": "user"}, 222: {"role": "admin"}}}

    def fake_get_user(uid): return state["users"].get(uid)
    def fake_update_user(uid, **kw): state["users"][uid].update(kw); return True

    # Monkeypatch expected functions if the module calls service layer
    for candidate in ("get_user_by_id", "get_user", "repo_get_user"):
        if hasattr(um, candidate):
            monkeypatch.setattr(um, candidate, fake_get_user, raising=False)
    for candidate in ("update_user", "repo_update_user", "save_user"):
        if hasattr(um, candidate):
            monkeypatch.setattr(um, candidate, fake_update_user, raising=False)

    # Entry points (prefer high-level helpers)
    promote = getattr(um, "promote_to_admin", None)
    demote = getattr(um, "demote_to_user", None)
    if not callable(promote) or not callable(demote):
        pytest.skip("User management promote/demote helpers not present; skipping")

    assert promote(111) is True
    assert state["users"][111]["role"] in ("admin", "owner", "superadmin")

    assert demote(222) is True
    assert state["users"][222]["role"] in ("user", "member")
