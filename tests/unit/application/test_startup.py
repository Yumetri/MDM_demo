from itertools import product
from unittest.mock import AsyncMock, Mock

import pytest

from mdm_demo.app import create_app
from mdm_demo.application.use_cases.brand import BrandUseCases
from mdm_demo.application.use_cases.brand_log import BrandLogUseCases
from mdm_demo.application.use_cases.company import CompanyUseCases
from mdm_demo.application.use_cases.company_log import CompanyLogUseCases
from mdm_demo.application.use_cases.model import ModelUseCases
from mdm_demo.application.use_cases.model_log import ModelLogUseCases

SERVICE_TYPES = {
    "service": CompanyUseCases,
    "log_service": CompanyLogUseCases,
    "model_service": ModelUseCases,
    "model_log_service": ModelLogUseCases,
    "brand_service": BrandUseCases,
    "brand_log_service": BrandLogUseCases,
}
SERVICE_STATE_NAMES = (
    "company_use_cases",
    "company_log_use_cases",
    "model_use_cases",
    "model_log_use_cases",
    "brand_use_cases",
    "brand_log_use_cases",
)


@pytest.mark.parametrize(
    "provided",
    [flags for flags in product((False, True), repeat=6) if any(flags) and not all(flags)],
)
def test_app_rejects_every_partial_service_combination(monkeypatch, provided):
    monkeypatch.delenv("CURSOR_SIGNING_KEY", raising=False)
    factory = Mock(side_effect=AssertionError("Partial injection must not create infrastructure"))
    monkeypatch.setattr("mdm_demo.app.create_session_factory", factory)
    services = {
        name: Mock(spec=service_type) if present else None
        for (name, service_type), present in zip(SERVICE_TYPES.items(), provided, strict=True)
    }

    with pytest.raises(ValueError, match="Provide all six services") as error:
        create_app(**services)

    assert str(error.value).split("Missing: ")[1].split(", ") == [
        name for name, value in services.items() if value is None
    ]
    factory.assert_not_called()


async def test_app_uses_all_injected_services_without_default_infrastructure(monkeypatch):
    monkeypatch.delenv("CURSOR_SIGNING_KEY", raising=False)
    factory = Mock(side_effect=AssertionError("Complete injection must not create infrastructure"))
    monkeypatch.setattr("mdm_demo.app.create_session_factory", factory)
    services = {name: Mock(spec=service_type) for name, service_type in SERVICE_TYPES.items()}

    app = create_app(**services)
    async with app.router.lifespan_context(app):
        for state_name, service in zip(SERVICE_STATE_NAMES, services.values(), strict=True):
            assert getattr(app.state, state_name) is service

    factory.assert_not_called()


@pytest.mark.parametrize("explicit_none", [False, True])
async def test_app_builds_default_services_and_disposes_engine(monkeypatch, explicit_none):
    monkeypatch.setenv("CURSOR_SIGNING_KEY", "test-only-signing-key-with-at-least-32-bytes")
    engine = Mock(dispose=AsyncMock())
    factory = Mock(return_value=(engine, Mock()))
    monkeypatch.setattr("mdm_demo.app.create_session_factory", factory)
    monkeypatch.setattr("mdm_demo.app.database_url", lambda: "test-database-url")

    app = create_app(**dict.fromkeys(SERVICE_TYPES)) if explicit_none else create_app()
    async with app.router.lifespan_context(app):
        for state_name, service_type in zip(
            SERVICE_STATE_NAMES, SERVICE_TYPES.values(), strict=True
        ):
            assert isinstance(getattr(app.state, state_name), service_type)
        factory.assert_called_once_with("test-database-url")
        engine.dispose.assert_not_awaited()

    engine.dispose.assert_awaited_once()


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
