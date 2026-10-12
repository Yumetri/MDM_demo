from datetime import UTC, datetime
from uuid import uuid4

import pytest

from mdm_demo.application.ports.cursors.company import CompanyBoundary
from mdm_demo.infrastructure.pagination.company_cursor import SignedCompanyCursor


async def create(client, capacity=256, unit="GB"):
    response = await client.post("/memories", json={"capacity": capacity, "unit": unit})
    assert response.status_code == 201, response.text
    return response.json()["data"]


async def test_crud_automatic_code_representation_noop_and_recreation(client):
    data = await create(client, 1, " tb ")
    path = f"/memories/{data['id']}"
    assert data["unit"] == "TB" and data["code"] == "1TB" and type(data["capacity"]) is int
    assert "capacity_gb" not in data
    assert (await client.get(path)).json()["data"] == data
    assert (await client.patch(path, json={"capacity": 1, "unit": "tb"})).json()["data"] == data
    assert len((await client.get(path + "/logs")).json()["data"]) == 1
    changed = await client.patch(path, json={"capacity": 1000, "unit": "GB"})
    assert changed.status_code == 200
    current = changed.json()["data"]
    assert current["code"] == "1000GB" and current["id"] == data["id"]
    assert (
        current["created_at"] == data["created_at"] and current["updated_at"] != data["updated_at"]
    )
    history = (await client.get(path + "/logs")).json()["data"]
    assert history[1]["before"]["capacity"] == 1 and history[1]["after"]["capacity"] == 1000
    assert history[1]["request_id"] == changed.json()["meta"]["request_id"]
    assert type(history[1]["after"]["capacity"]) is int
    deleted = await client.delete(path)
    assert deleted.status_code == 204 and deleted.content == b""
    assert (await client.get(path)).status_code == 404 and (
        await client.delete(path)
    ).status_code == 404
    history = (await client.get(path + "/logs")).json()["data"]
    assert [log["operation"] for log in history] == ["create", "update", "delete"]
    assert history[-1]["after"] is None
    new = await create(client, 1, "TB")
    assert new["id"] != data["id"]
    assert len((await client.get(f"/memories/{new['id']}/logs")).json()["data"]) == 1
    assert len((await client.get(path + "/logs")).json()["data"]) == 3


async def test_equivalent_duplicates_and_update_rollback(client):
    first = await create(client, 1, "TB")
    second = await create(client, 256, "GB")
    duplicate = await client.post("/memories", json={"capacity": 1000, "unit": "GB"})
    assert duplicate.status_code == 409
    error = duplicate.json()["error"]
    assert error["code"] == "MEMORY_CAPACITY_DUPLICATE"
    assert error["message"] == "이미 존재하는 저장공간 용량입니다."
    assert error["details"][0]["field"] == "body.capacity"
    path = f"/memories/{second['id']}"
    duplicate = await client.patch(path, json={"capacity": 1000, "unit": "GB"})
    assert duplicate.status_code == 409
    assert (await client.get(path)).json()["data"] == second
    assert len((await client.get(path + "/logs")).json()["data"]) == 1
    assert (await client.get(f"/memories/{first['id']}")).json()["data"] == first


async def test_cursor_boundaries_order_and_context(client, signing_key):
    items = [await create(client, capacity) for capacity in [512, 128, 256]]
    page = (await client.get("/memories", params={"limit": 1})).json()
    assert page["data"][0]["id"] == items[0]["id"]
    token = page["meta"]["page"]["next_cursor"]
    await client.delete(f"/memories/{items[0]['id']}")
    remaining = (await client.get("/memories", params={"limit": 100, "cursor": token})).json()
    assert [item["id"] for item in remaining["data"]] == [items[1]["id"], items[2]["id"]]
    assert remaining["meta"]["page"] == {"next_cursor": None, "has_next": False}
    foreign = SignedCompanyCursor(signing_key).encode(CompanyBoundary(datetime.now(UTC), uuid4()))
    for bad in ["", "not-a-cursor", token[:-1] + ("a" if token[-1] != "a" else "b"), foreign]:
        response = await client.get("/memories", params={"cursor": bad})
        assert response.status_code == 400 and response.json()["error"]["code"] == "INVALID_CURSOR"
    assert (
        await client.get(f"/memories/{items[1]['id']}/logs", params={"cursor": token})
    ).status_code == 400
    assert (await client.get("/memories", params={"unknown": "ignored"})).status_code == 200


@pytest.mark.parametrize("limit", [0, 101, "many"])
async def test_invalid_limit(client, limit):
    response = await client.get("/memories", params={"limit": limit})
    assert response.status_code == 422


async def test_missing_and_invalid_targets(client):
    for identity, status in [(str(uuid4()), 404), ("invalid", 422)]:
        path = f"/memories/{identity}"
        assert (await client.get(path)).status_code == status
        assert (
            await client.patch(path, json={"capacity": 256, "unit": "GB"})
        ).status_code == status
        assert (await client.delete(path)).status_code == status
