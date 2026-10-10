import pytest

from mdm_demo.app import create_app


@pytest.mark.parametrize("key", [None, "", "short"])
async def test_app_rejects_missing_or_short_cursor_key(monkeypatch, key):
    if key is None:
        monkeypatch.delenv("CURSOR_SIGNING_KEY", raising=False)
    else:
        monkeypatch.setenv("CURSOR_SIGNING_KEY", key)
    app = create_app()
    with pytest.raises((KeyError, ValueError)):
        async with app.router.lifespan_context(app):
            pytest.fail("Application must not start without a valid signing key")
