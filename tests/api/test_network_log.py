from datetime import UTC, datetime
from uuid import UUID, uuid4

from mdm_demo.domain.entities.network import Network
from mdm_demo.domain.entities.network_log import NetworkLog
from mdm_demo.infrastructure.persistence.units_of_work.network import SqlAlchemyNetworkUnitOfWork


async def test_history_survives_delete_and_code_reuse(client):
    created = await client.post("/networks", json={"name": "KOREA", "code": "KOR"})
    network_id = created.json()["data"]["id"]
    path = f"/networks/{network_id}"
    noop = await client.patch(path, json={"name": " korea "})
    assert noop.status_code == 200
    renamed = await client.patch(path, json={"name": "New Name"})
    deleted = await client.delete(path)
    replacement = await client.post("/networks", json={"name": "KOREA", "code": "KOR"})
    assert replacement.json()["data"]["id"] != network_id
    response = await client.get(path + "/logs")
    assert response.status_code == 200
    assert response.headers["x-request-id"] == response.json()["meta"]["request_id"]
    history = response.json()["data"][::-1]
    assert [item["operation"] for item in history] == ["create", "update", "delete"]
    assert [item["request_id"] for item in history] == [
        r.headers["x-request-id"] for r in [created, renamed, deleted]
    ]
    assert history[0]["before"] is None
    assert history[1]["before"] == history[0]["after"]
    assert history[2]["before"] == history[1]["after"]
    assert history[2]["after"] is None
    assert all(item["network_id"] == network_id for item in history)
    for item in history:
        single = await client.get("/network-logs/" + item["id"])
        assert single.status_code == 200 and single.json()["data"] == item
        assert single.json()["meta"]["request_id"] != item["request_id"]
        assert single.headers["x-request-id"] == single.json()["meta"]["request_id"]
    assert (await client.get(path)).status_code == 404
    new_history = await client.get("/networks/" + replacement.json()["data"]["id"] + "/logs")
    assert len(new_history.json()["data"]) == 1
    assert (await client.get(path + "/logs")).json()["data"] == history[::-1]


async def test_empty_missing_invalid_and_read_only(client):
    missing = str(uuid4())
    empty = await client.get(f"/networks/{missing}/logs")
    assert empty.status_code == 200
    assert empty.json()["data"] == []
    assert empty.json()["meta"]["page"] == {"has_next": False, "next_cursor": None}
    missing_log = await client.get("/network-logs/" + missing)
    assert missing_log.status_code == 404
    assert missing_log.json()["error"]["code"] == "NOT_FOUND"
    for path in ["/networks/not-a-uuid/logs", "/network-logs/not-a-uuid"]:
        assert (await client.get(path)).status_code == 422
    for method in ["POST", "PATCH", "DELETE"]:
        for path in [f"/networks/{missing}/logs", "/network-logs/" + missing]:
            assert (await client.request(method, path, json={})).status_code == 405


async def test_log_cursor_scope_boundaries_and_limit(client):
    created = await client.post("/networks", json={"name": "KOREA", "code": "KOR"})
    network_id = created.json()["data"]["id"]
    path = f"/networks/{network_id}"
    await client.patch(path, json={"name": "New"})
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
        await client.get(f"/networks/{uuid4()}/logs", params={"cursor": cursor})
    ).status_code == 400
    assert (await client.get("/networks", params={"cursor": cursor})).status_code == 400
    for name in ["Alpha", "Bravo"]:
        await client.post("/networks", json={"name": name, "code": name[:3]})
    network_page = await client.get("/networks", params={"limit": 1})
    network_cursor = network_page.json()["meta"]["page"]["next_cursor"]
    assert (await client.get(path + "/logs", params={"cursor": network_cursor})).status_code == 400
    for limit in [0, 101, "many"]:
        assert (await client.get(path + "/logs", params={"limit": limit})).status_code == 422


async def test_same_timestamp_log_pagination(client, database):
    _, factory = database
    network = Network.create("Same", "SMA")
    other = Network.create("Other", "OTH")
    now = datetime.now(UTC)
    async with SqlAlchemyNetworkUnitOfWork(factory) as uow:
        for index, target in [(3, network), (2, other), (1, network)]:
            await uow.network_logs.add(
                NetworkLog(
                    UUID(int=index), target.id, "create", now, uuid4(), None, target.snapshot()
                )
            )
        await uow.commit()
    path = f"/networks/{network.id}/logs"
    first = await client.get(path, params={"limit": 1})
    second = await client.get(
        path, params={"limit": 1, "cursor": first.json()["meta"]["page"]["next_cursor"]}
    )
    assert first.json()["data"][0]["id"] == str(UUID(int=3))
    assert second.json()["data"][0]["id"] == str(UUID(int=1))
    assert second.json()["meta"]["page"]["has_next"] is False
