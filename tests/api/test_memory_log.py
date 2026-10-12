from uuid import uuid4


async def test_logs_missing_ids_pagination_and_target_scope(client):
    created = await client.post("/memories", json={"capacity": 256, "unit": "GB"})
    identity = created.json()["data"]["id"]
    path = f"/memories/{identity}"
    await client.patch(path, json={"capacity": 512, "unit": "GB"})
    await client.delete(path)
    first = (await client.get(path + "/logs", params={"limit": 1})).json()
    log = first["data"][0]
    assert log["operation"] == "create" and log["before"] is None
    single = await client.get(f"/memory-logs/{log['id']}")
    assert single.status_code == 200 and single.json()["data"] == log
    assert single.json()["meta"]["request_id"] != log["request_id"]
    token = first["meta"]["page"]["next_cursor"]
    rest = (await client.get(path + "/logs", params={"limit": 100, "cursor": token})).json()
    assert [item["operation"] for item in rest["data"]] == ["update", "delete"]
    assert rest["data"][0]["before"] == log["after"]
    assert rest["data"][1]["before"] == rest["data"][0]["after"]
    other = str(uuid4())
    assert (await client.get(f"/memories/{other}/logs")).json()["data"] == []
    assert (
        await client.get(f"/memories/{other}/logs", params={"cursor": token})
    ).status_code == 400
    assert (await client.get("/memories", params={"cursor": token})).status_code == 400
    assert (await client.get(f"/memory-logs/{other}")).status_code == 404
    assert (await client.get("/memory-logs/invalid")).status_code == 422
    assert (await client.get("/memories/invalid/logs")).status_code == 422
    for invalid in ["", "not-a-cursor"]:
        assert (await client.get(path + "/logs", params={"cursor": invalid})).status_code == 400
    for limit in [0, 101]:
        assert (await client.get(path + "/logs", params={"limit": limit})).status_code == 422
