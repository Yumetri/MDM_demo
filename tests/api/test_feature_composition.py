from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from mdm_demo.composition.registry import DEFAULT_MODULES


@pytest.mark.parametrize("module", DEFAULT_MODULES, ids=lambda module: module.name)
async def test_isolated_feature_create_and_log_share_transaction(
    app_factory, module, database, monkeypatch
):
    dispose = AsyncMock(wraps=type(database[0]).dispose)
    monkeypatch.setattr(type(database[0]), "dispose", dispose)
    app = app_factory(modules=(module,))
    collection = {
        "company": "companies",
        "country": "countries",
        "category": "categories",
        "memory": "memories",
    }.get(module.name, module.name + "s")
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            if module.name == "memory":
                payload = {"capacity": 256, "unit": "GB"}
            elif module.name == "year":
                payload = {"year": 2024}
            else:
                payload = {"name": "Isolated", "code": "ISO"}
            created = await client.post(f"/{collection}", json=payload)
            assert created.status_code == 201
            entity = created.json()["data"]
            logs = await client.get(f"/{collection}/{entity['id']}/logs")
            assert logs.status_code == 200
            assert logs.json()["data"][0]["after"]["id"] == entity["id"]
            assert logs.json()["data"][0]["operation"] == "create"
            schema = (await client.get("/openapi.json")).json()
            assert f"/{collection}" in schema["paths"]
            assert len(schema["paths"]) == 5
    dispose.assert_not_awaited()
    # The fixture owns disposal; another app can borrow the same runtime.
    second = app_factory(modules=(module,))
    async with second.router.lifespan_context(second):
        async with AsyncClient(
            transport=ASGITransport(app=second), base_url="http://test"
        ) as client:
            response = await client.get(f"/{collection}/{entity['id']}")
            assert response.status_code == 200
    dispose.assert_not_awaited()
