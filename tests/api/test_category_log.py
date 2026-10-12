from datetime import UTC, datetime
from uuid import UUID, uuid4

from mdm_demo.domain.entities.category import Category
from mdm_demo.domain.entities.category_log import CategoryLog
from mdm_demo.infrastructure.persistence.units_of_work.category import SqlAlchemyCategoryUnitOfWork


async def test_history_survives_delete_and_code_reuse(client):
    created = await client.post("/categories", json={"name": "SMARTPHONE", "code": "SMA"})
    category_id = created.json()["data"]["id"]
    path = f"/categories/{category_id}"
    noop = await client.patch(path, json={"name": " smartphone "})
    assert noop.status_code == 200
    renamed = await client.patch(path, json={"name": "New Name"})
    deleted = await client.delete(path)
    replacement = await client.post("/categories", json={"name": "SMARTPHONE", "code": "SMA"})
    assert replacement.json()["data"]["id"] != category_id
    response = await client.get(path + "/logs")
    assert response.status_code == 200
    assert response.headers["x-request-id"] == response.json()["meta"]["request_id"]
    history = response.json()["data"]
    assert [item["operation"] for item in history] == ["create", "update", "delete"]
    assert [item["request_id"] for item in history] == [
        r.headers["x-request-id"] for r in [created, renamed, deleted]
    ]
    assert history[0]["before"] is None
    assert history[1]["before"] == history[0]["after"]
    assert history[2]["before"] == history[1]["after"]
    assert history[2]["after"] is None
    assert all(item["category_id"] == category_id for item in history)
    for item in history:
        single = await client.get("/category-logs/" + item["id"])
        assert single.status_code == 200 and single.json()["data"] == item
        assert single.json()["meta"]["request_id"] != item["request_id"]
        assert single.headers["x-request-id"] == single.json()["meta"]["request_id"]
    assert (await client.get(path)).status_code == 404
    new_history = await client.get("/categories/" + replacement.json()["data"]["id"] + "/logs")
    assert len(new_history.json()["data"]) == 1
    assert (await client.get(path + "/logs")).json()["data"] == history


async def test_empty_missing_invalid_and_read_only(client):
    missing = str(uuid4())
    empty = await client.get(f"/categories/{missing}/logs")
    assert empty.status_code == 200
    assert empty.json()["data"] == []
    assert empty.json()["meta"]["page"] == {"has_next": False, "next_cursor": None}
    missing_log = await client.get("/category-logs/" + missing)
    assert missing_log.status_code == 404
    assert missing_log.json()["error"]["code"] == "NOT_FOUND"
    for path in ["/categories/not-a-uuid/logs", "/category-logs/not-a-uuid"]:
        assert (await client.get(path)).status_code == 422
    for method in ["POST", "PATCH", "DELETE"]:
        for path in [f"/categories/{missing}/logs", "/category-logs/" + missing]:
            assert (await client.request(method, path, json={})).status_code == 405


async def test_log_cursor_scope_boundaries_and_limit(client):
    created = await client.post("/categories", json={"name": "SMARTPHONE", "code": "SMA"})
    category_id = created.json()["data"]["id"]
    path = f"/categories/{category_id}"
    await client.patch(path, json={"name": "New"})
    await client.delete(path)
    first = await client.get(path + "/logs", params={"limit": 1})
    cursor = first.json()["meta"]["page"]["next_cursor"]
    assert cursor and first.json()["meta"]["page"]["has_next"]
    second = await client.get(path + "/logs", params={"limit": 100, "cursor": cursor})
    assert [item["operation"] for item in first.json()["data"] + second.json()["data"]] == [
        "create",
        "update",
        "delete",
    ]
    assert second.json()["meta"]["page"] == {"next_cursor": None, "has_next": False}
    for invalid in ["", "bad", cursor + "x", "a" * 2049]:
        response = await client.get(path + "/logs", params={"cursor": invalid})
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_CURSOR"
    assert (
        await client.get(f"/categories/{uuid4()}/logs", params={"cursor": cursor})
    ).status_code == 400
    assert (await client.get("/categories", params={"cursor": cursor})).status_code == 400
    for name in ["Alpha", "Bravo"]:
        await client.post("/categories", json={"name": name, "code": name[:3]})
    category_page = await client.get("/categories", params={"limit": 1})
    category_cursor = category_page.json()["meta"]["page"]["next_cursor"]
    assert (await client.get(path + "/logs", params={"cursor": category_cursor})).status_code == 400
    for limit in [0, 101, "many"]:
        assert (await client.get(path + "/logs", params={"limit": limit})).status_code == 422


async def test_same_timestamp_log_pagination(client, database):
    _, factory = database
    category = Category.create("Same", "SMA")
    other = Category.create("Other", "OTH")
    now = datetime.now(UTC)
    async with SqlAlchemyCategoryUnitOfWork(factory) as uow:
        for index, target in [(3, category), (2, other), (1, category)]:
            await uow.category_logs.add(
                CategoryLog(
                    UUID(int=index), target.id, "create", now, uuid4(), None, target.snapshot()
                )
            )
        await uow.commit()
    path = f"/categories/{category.id}/logs"
    first = await client.get(path, params={"limit": 1})
    second = await client.get(
        path, params={"limit": 1, "cursor": first.json()["meta"]["page"]["next_cursor"]}
    )
    assert first.json()["data"][0]["id"] == str(UUID(int=1))
    assert second.json()["data"][0]["id"] == str(UUID(int=3))
    assert second.json()["meta"]["page"]["has_next"] is False
