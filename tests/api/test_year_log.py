from datetime import UTC, datetime
from uuid import UUID, uuid4

from mdm_demo.domain.entities.year import Year
from mdm_demo.domain.entities.year_log import YearLog
from mdm_demo.infrastructure.persistence.units_of_work.year import SqlAlchemyYearUnitOfWork


async def test_history_survives_delete_and_code_reuse(client):
    created = await client.post("/years", json={"year": 2024})
    year_id = created.json()["data"]["id"]
    path = f"/years/{year_id}"
    noop = await client.patch(path, json={"year": 2024})
    assert noop.status_code == 200
    renamed = await client.patch(path, json={"year": 2025})
    deleted = await client.delete(path)
    replacement = await client.post("/years", json={"year": 2024})
    assert replacement.json()["data"]["id"] != year_id
    response = await client.get(path + "/logs")
    assert response.status_code == 200
    assert response.headers["x-request-id"] == response.json()["meta"]["request_id"]
    history = response.json()["data"]
    assert [item["operation"] for item in history] == ["delete", "update", "create"]
    assert [item["request_id"] for item in history] == [
        r.headers["x-request-id"] for r in [deleted, renamed, created]
    ]
    assert history[0]["after"] is None
    assert history[1]["after"] == history[0]["before"]
    assert history[2]["after"] == history[1]["before"]
    assert history[2]["before"] is None
    assert all(item["year_id"] == year_id for item in history)
    for item in history:
        single = await client.get("/year-logs/" + item["id"])
        assert single.status_code == 200 and single.json()["data"] == item
        assert single.json()["meta"]["request_id"] != item["request_id"]
        assert single.headers["x-request-id"] == single.json()["meta"]["request_id"]
    assert (await client.get(path)).status_code == 404
    new_history = await client.get("/years/" + replacement.json()["data"]["id"] + "/logs")
    assert len(new_history.json()["data"]) == 1
    assert (await client.get(path + "/logs")).json()["data"] == history


async def test_empty_missing_invalid_and_read_only(client):
    missing = str(uuid4())
    empty = await client.get(f"/years/{missing}/logs")
    assert empty.status_code == 200
    assert empty.json()["data"] == []
    assert empty.json()["meta"]["page"] == {"has_next": False, "next_cursor": None}
    missing_log = await client.get("/year-logs/" + missing)
    assert missing_log.status_code == 404
    assert missing_log.json()["error"]["code"] == "NOT_FOUND"
    for path in ["/years/not-a-uuid/logs", "/year-logs/not-a-uuid"]:
        assert (await client.get(path)).status_code == 422
    for method in ["POST", "PATCH", "DELETE"]:
        for path in [f"/years/{missing}/logs", "/year-logs/" + missing]:
            assert (await client.request(method, path, json={})).status_code == 405


async def test_log_cursor_scope_boundaries_and_limit(client):
    created = await client.post("/years", json={"year": 2024})
    year_id = created.json()["data"]["id"]
    path = f"/years/{year_id}"
    await client.patch(path, json={"year": 2025})
    await client.delete(path)
    first = await client.get(path + "/logs", params={"limit": 1})
    cursor = first.json()["meta"]["page"]["next_cursor"]
    assert cursor and first.json()["meta"]["page"]["has_next"]
    second = await client.get(path + "/logs", params={"limit": 100, "cursor": cursor})
    assert [item["operation"] for item in first.json()["data"] + second.json()["data"]] == [
        "delete",
        "update",
        "create",
    ]
    assert second.json()["meta"]["page"] == {"next_cursor": None, "has_next": False}
    for invalid in ["", "bad", cursor + "x", "a" * 2049]:
        response = await client.get(path + "/logs", params={"cursor": invalid})
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_CURSOR"
    assert (
        await client.get(f"/years/{uuid4()}/logs", params={"cursor": cursor})
    ).status_code == 400
    assert (await client.get("/years", params={"cursor": cursor})).status_code == 400
    for value in [2026, 2027]:
        await client.post("/years", json={"year": value})
    year_page = await client.get("/years", params={"limit": 1})
    year_cursor = year_page.json()["meta"]["page"]["next_cursor"]
    assert (await client.get(path + "/logs", params={"cursor": year_cursor})).status_code == 400
    for limit in [0, 101, "many"]:
        assert (await client.get(path + "/logs", params={"limit": limit})).status_code == 422


async def test_same_timestamp_log_pagination(client, database):
    _, factory = database
    year = Year.create(2024)
    other = Year.create(2025)
    now = datetime.now(UTC)
    async with SqlAlchemyYearUnitOfWork(factory) as uow:
        for index, target in [(3, year), (2, other), (1, year)]:
            await uow.year_logs.add(
                YearLog(UUID(int=index), target.id, "create", now, uuid4(), None, target.snapshot())
            )
        await uow.commit()
    path = f"/years/{year.id}/logs"
    first = await client.get(path, params={"limit": 1})
    second = await client.get(
        path, params={"limit": 1, "cursor": first.json()["meta"]["page"]["next_cursor"]}
    )
    assert first.json()["data"][0]["id"] == str(UUID(int=3))
    assert second.json()["data"][0]["id"] == str(UUID(int=1))
    assert second.json()["meta"]["page"]["has_next"] is False
