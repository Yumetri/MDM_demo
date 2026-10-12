from uuid import uuid4

import pytest


async def test_crud_code_changes_noop_duplicate_and_deleted_boundary(client):
    ids = []
    for value in [2024, 2026, 2025]:
        response = await client.post("/years", json={"year": value})
        assert response.status_code == 201
        row = response.json()["data"]
        assert row["code"] == str(value) and type(row["year"]) is int
        ids.append(row["id"])
    page = (await client.get("/years", params={"limit": 1})).json()
    assert page["data"][0]["year"] == 2026
    cursor = page["meta"]["page"]["next_cursor"]
    assert (await client.delete("/years/" + ids[1])).status_code == 204
    next_page = (await client.get("/years", params={"limit": 100, "cursor": cursor})).json()
    assert [r["year"] for r in next_page["data"]] == [2025, 2024]
    path = "/years/" + ids[0]
    original = (await client.get(path)).json()["data"]
    assert (await client.patch(path, json={"year": 2024})).json()["data"] == original
    for method, target in [("post", "/years"), ("patch", path)]:
        conflict = await getattr(client, method)(target, json={"year": 2025})
        assert conflict.status_code == 409 and conflict.json()["error"]["code"] == "YEAR_DUPLICATE"
        assert conflict.json()["error"]["message"] == "이미 존재하는 출시 연도입니다."
    changed = (await client.patch(path, json={"year": 2027})).json()["data"]
    assert changed["id"] == original["id"] and changed["code"] == "2027"
    assert len((await client.get(path + "/logs")).json()["data"]) == 2
    missing = "/years/" + str(uuid4())
    assert (await client.get(missing)).status_code == 404
    assert (await client.patch(missing, json={"year": 2024})).status_code == 404
    assert (await client.delete(missing)).status_code == 404
    assert (await client.get("/years/not-a-uuid")).status_code == 422


@pytest.mark.parametrize("limit", [0, 101, "many"])
async def test_limit_errors(client, limit):
    assert (await client.get("/years", params={"limit": limit})).status_code == 422


async def test_cross_dimension_cursor_and_empty_pages(client):
    for value in [2024, 2025]:
        await client.post("/years", json={"year": value})
    token = (await client.get("/years", params={"limit": 1})).json()["meta"]["page"]["next_cursor"]
    assert (await client.get("/models", params={"cursor": token})).status_code == 400
    for name in ["Alpha", "Bravo"]:
        await client.post("/models", json={"name": name})
    foreign = (await client.get("/models", params={"limit": 1})).json()["meta"]["page"][
        "next_cursor"
    ]
    for invalid in ["", "bad", token + "x", foreign, "x" * 2049]:
        assert (await client.get("/years", params={"cursor": invalid})).status_code == 400
