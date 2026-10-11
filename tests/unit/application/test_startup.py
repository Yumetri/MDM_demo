from contextlib import asynccontextmanager
from dataclasses import replace
from unittest.mock import AsyncMock, Mock

import pytest

from mdm_demo.app import create_app
from mdm_demo.composition import runtime
from mdm_demo.composition.feature import FeatureModule
from mdm_demo.composition.registry import DEFAULT_MODULES
from mdm_demo.composition.runtime import RuntimeResources


@pytest.fixture
def owned_engine(monkeypatch, signing_key):
    monkeypatch.setenv("CURSOR_SIGNING_KEY", signing_key)
    engine = Mock(dispose=AsyncMock())
    factory = Mock(return_value=(engine, Mock()))
    monkeypatch.setattr(runtime, "create_session_factory", factory)
    monkeypatch.setattr(runtime, "database_url", lambda: "test-database-url")
    return engine, factory


@pytest.mark.parametrize("modules", [(module,) for module in DEFAULT_MODULES] + [DEFAULT_MODULES])
async def test_selected_modules_are_ready_and_owned_engine_is_disposed(owned_engine, modules):
    engine, factory = owned_engine
    app = create_app(modules=modules)
    assert any(path != "/health" for path in app.openapi()["paths"])
    async with app.router.lifespan_context(app):
        for module in modules:
            for name in module.state_names:
                assert getattr(app.state, name) is not None
        engine.dispose.assert_not_awaited()
    factory.assert_called_once_with("test-database-url")
    engine.dispose.assert_awaited_once()
    for module in modules:
        for name in module.state_names:
            assert not hasattr(app.state, name)


@pytest.mark.parametrize("key", [None, "", "short"])
async def test_invalid_key_fails_before_creating_owned_engine(monkeypatch, key):
    if key is None:
        monkeypatch.delenv("CURSOR_SIGNING_KEY", raising=False)
    else:
        monkeypatch.setenv("CURSOR_SIGNING_KEY", key)
    factory = Mock(side_effect=AssertionError("Invalid key must not allocate an engine"))
    monkeypatch.setattr(runtime, "create_session_factory", factory)
    app = create_app()
    with pytest.raises((KeyError, ValueError)):
        async with app.router.lifespan_context(app):
            pytest.fail("Invalid configuration must fail during startup")
    factory.assert_not_called()


async def test_borrowed_runtime_does_not_create_default_resources(monkeypatch, signing_key):
    factory = Mock(side_effect=AssertionError("Must not allocate a default engine"))
    monkeypatch.setattr(runtime, "create_session_factory", factory)
    entered = []
    resources = RuntimeResources(Mock(), signing_key)

    @asynccontextmanager
    async def borrowed_runtime():
        entered.append("enter")
        try:
            yield resources
        finally:
            entered.append("exit")

    app = create_app(runtime_factory=borrowed_runtime)
    async with app.router.lifespan_context(app):
        assert entered == ["enter"]
    assert entered == ["enter", "exit"]
    factory.assert_not_called()


@pytest.mark.parametrize("failure_mode", ["exception", "missing_service"])
async def test_failed_feature_initialization_releases_engine_and_partial_state(
    owned_engine, failure_mode
):
    engine, _ = owned_engine

    def broken(app, resources):
        app.state.partial_service = object()
        if failure_mode == "exception":
            raise RuntimeError("injected initialization failure")

    module = FeatureModule("broken", (), broken, ("partial_service", "missing_service"))
    app = create_app(modules=(*DEFAULT_MODULES, module))
    with pytest.raises((RuntimeError, ValueError)):
        async with app.router.lifespan_context(app):
            pytest.fail("Incomplete feature must not serve requests")
    engine.dispose.assert_awaited_once()
    assert not hasattr(app.state, "partial_service")
    for selected in DEFAULT_MODULES:
        for name in selected.state_names:
            assert not hasattr(app.state, name)


@pytest.mark.parametrize("kind", ["feature", "service", "route"])
def test_duplicate_registration_fails_before_startup(kind):
    original = DEFAULT_MODULES[0]
    duplicate = {
        "feature": original,
        "service": replace(original, name="other"),
        "route": replace(original, name="other", state_names=()),
    }[kind]
    with pytest.raises(ValueError, match="Duplicate"):
        create_app(modules=(original, duplicate))


async def test_separate_app_instances_do_not_share_service_state(signing_key):
    @asynccontextmanager
    async def borrowed_runtime():
        yield RuntimeResources(Mock(), signing_key)

    first = create_app(runtime_factory=borrowed_runtime)
    second = create_app(runtime_factory=borrowed_runtime)
    async with first.router.lifespan_context(first), second.router.lifespan_context(second):
        for module in DEFAULT_MODULES:
            for name in module.state_names:
                assert getattr(first.state, name) is not getattr(second.state, name)


async def test_test_dependency_override_serves_without_default_resources(monkeypatch, signing_key):
    from httpx import ASGITransport, AsyncClient

    from mdm_demo.application.errors import ApplicationError
    from mdm_demo.composition.country import module
    from mdm_demo.presentation.dependencies.country import country_use_cases

    factory = Mock(side_effect=AssertionError("No database allocation in isolated HTTP test"))
    monkeypatch.setattr(runtime, "create_session_factory", factory)

    @asynccontextmanager
    async def borrowed_runtime():
        yield RuntimeResources(Mock(), signing_key)

    fake_service = Mock(get=AsyncMock(side_effect=ApplicationError("NOT_FOUND")))
    app = create_app(modules=(module,), runtime_factory=borrowed_runtime)
    app.dependency_overrides[country_use_cases] = lambda: fake_service
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/countries/11111111-1111-4111-8111-111111111111")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    fake_service.get.assert_awaited_once()
    factory.assert_not_called()


async def test_new_module_can_be_registered_without_changing_existing_modules(owned_engine):
    from fastapi import APIRouter
    from httpx import ASGITransport, AsyncClient

    router = APIRouter()

    @router.get("/extension")
    async def extension():
        return {"ready": True}

    def configure(app, resources):
        app.state.extension_service = object()

    module = FeatureModule("extension", (router,), configure, ("extension_service",))
    app = create_app(modules=(*DEFAULT_MODULES, module))
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/extension")
        assert response.status_code == 200
        assert response.json() == {"ready": True}
        assert "/extension" in app.openapi()["paths"]
        for selected in DEFAULT_MODULES:
            for name in selected.state_names:
                assert getattr(app.state, name) is not None
    assert not hasattr(app.state, "extension_service")
