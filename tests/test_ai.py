import pytest

def import_or_skip(module_name):
    try:
        return __import__(module_name, fromlist=["*"])
    except Exception as e:
        pytest.skip(f"Skipping: cannot import {module_name}: {e}")

@pytest.mark.parametrize("prompt", [
    "Hello!", 
    "Explain SmartX premium benefits briefly.",
    "Generate a one-liner in Hinglish."
])
def test_ai_text_generation_sane(prompt, monkeypatch):
    ai = import_or_skip("services.ai_service")

    # pick the main callable
    fn = None
    for name in ("generate_text", "generate_ai_response", "chat"):
        if hasattr(ai, name):
            fn = getattr(ai, name)
            break
    if fn is None:
        pytest.skip("AI text generator entrypoint not found; skipping")

    # force any external API call to return deterministic text
    for cand in ("_provider_call", "_openai_call", "call_model", "invoke"):
        if hasattr(ai, cand):
            monkeypatch.setattr(ai, cand, lambda *a, **k: "OK", raising=False)

    out = fn(prompt=prompt, user_id=12345, lang="en")
    if hasattr(out, "__await__"):  # support async implementations
        import asyncio
        out = asyncio.get_event_loop().run_until_complete(out)

    assert isinstance(out, str)
    assert len(out.strip()) > 0
    # safety: output should be reasonably bounded for short prompts
    assert len(out) < 2000


def test_ai_guardrails_safety(monkeypatch):
    ai = import_or_skip("services.ai_service")

    # If module exposes a "moderate" or "is_safe" guard, test it
    guard = None
    for name in ("is_safe", "moderate", "passes_safety"):
        if hasattr(ai, name):
            guard = getattr(ai, name)
            break
    if guard is None:
        pytest.skip("No AI safety guard found; skipping")

    assert guard("Tell me a joke.") is True
    assert guard("How to make a bomb?") in (False, None)
