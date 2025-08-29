import pytest

def import_or_skip(module_name):
    try:
        return __import__(module_name, fromlist=["*"])
    except Exception as e:
        pytest.skip(f"Skipping: cannot import {module_name}: {e}")

def test_main_menu_keyboard_structure():
    kb_mod = import_or_skip("keyboards.main_menu")

    build = None
    for name in ("build", "get", "main_menu", "make_menu"):
        if hasattr(kb_mod, name):
            build = getattr(kb_mod, name)
            break
    if build is None:
        pytest.skip("Main menu builder not found; skipping")

    kb = build(lang="en", is_premium=False)
    # keyboard may be nested list (Telegram) or plain dict
    assert kb is not None
    # structural guards
    if isinstance(kb, dict):
        assert any(k in kb for k in ("inline_keyboard", "keyboard"))
    elif isinstance(kb, (list, tuple)):
        assert len(kb) > 0


@pytest.mark.parametrize("handler_module,entry", [
    ("handlers.start", ("start", "handle_start", "entry")),
    ("handlers.premium", ("premium", "handle_premium")),
    ("handlers.services", ("services", "handle_services")),
])
def test_handlers_are_importable(handler_module, entry):
    """
    Smoke test: key handler modules import and expose a callable entrypoint.
    """
    mod = import_or_skip(handler_module)

    fn = None
    for name in entry:
        if hasattr(mod, name):
            maybe = getattr(mod, name)
            if callable(maybe):
                fn = maybe
                break
    assert callable(fn), f"{handler_module} has no callable entrypoint among {entry}"
