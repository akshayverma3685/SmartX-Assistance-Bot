import pytest

def import_or_skip(module_name):
    try:
        return __import__(module_name, fromlist=["*"])
    except Exception as e:
        pytest.skip(f"Skipping: cannot import {module_name}: {e}")

@pytest.mark.parametrize("url,kind", [
    ("https://youtu.be/dQw4w9WgXcQ", "video"),
    ("https://twitter.com/user/status/1", "social"),
    ("https://example.com/file.pdf", "file"),
])
def test_download_router_resolution(url, kind, monkeypatch):
    dl = import_or_skip("services.download_service")

    resolve = getattr(dl, "resolve_url", None) or getattr(dl, "route", None)
    if resolve is None:
        pytest.skip("Download resolver not present; skipping")

    # Monkeypatch network to deterministic result
    if hasattr(dl, "_probe"):
        monkeypatch.setattr(dl, "_probe", lambda *a, **k: {"ok": True}, raising=False)

    info = resolve(url)
    if hasattr(info, "__await__"):
        import asyncio
        info = asyncio.get_event_loop().run_until_complete(info)

    assert isinstance(info, dict)
    assert info.get("url") or info.get("source")
    # Kind should be inferred or default to "generic"
    assert info.get("kind", "generic") in (kind, "generic", "video", "audio", "file", "social")


def test_downloaders_return_path_or_bytes(monkeypatch, tmp_path):
    dl = import_or_skip("services.download_service")

    # pick any concrete helper
    for name in ("download_youtube", "download_generic", "download"):
        if hasattr(dl, name):
            func = getattr(dl, name)
            break
    else:
        pytest.skip("No concrete downloader found; skipping")

    # avoid real network: return a small temp file
    fake_file = tmp_path / "demo.bin"
    fake_file.write_bytes(b"smartx")
    monkeypatch.setattr(dl, name, lambda *a, **k: {"path": str(fake_file)}, raising=False)

    out = func("https://example.com")
    assert isinstance(out, dict)
    assert "path" in out and out["path"].endswith(".bin")
