import json
from unicodedata import normalize
from uuid import uuid4

import pytest


async def test_crud_normalization_noop_delete_reuse(client):
    created = await client.post("/networks", json={"name": " korea ", "code": " kor "})
    assert created.status_code == 201
    network = created.json()["data"]
    assert (network["name"], network["code"]) == ("KOREA", "KOR")
    path = "/networks/" + network["id"]
    assert (await client.get(path)).json()["data"] == network
    assert (await client.patch(path, json={"name": " Korea "})).json()["data"] == network
    assert len((await client.get(path + "/logs")).json()["data"]) == 1
    updated = await client.patch(path, json={"name": "대한민국"})
    assert updated.status_code == 200 and updated.json()["data"]["code"] == "KOR"
    assert (await client.patch(path, json={"name": normalize("NFD", "대한민국")})).json()[
        "data"
    ] == updated.json()["data"]
    deleted = await client.delete(path)
    assert deleted.status_code == 204 and deleted.content == b""
    for response in [created, updated, deleted]:
        assert response.headers["x-request-id"]
        if response.status_code != 204:
            assert response.json()["meta"]["request_id"] == response.headers["x-request-id"]
    for method in ["GET", "DELETE", "PATCH"]:
        assert (await client.request(method, path, json={"name": "New"})).status_code == 404
    replacement = await client.post("/networks", json={"name": "대한민국", "code": "KOR"})
    assert replacement.status_code == 201 and replacement.json()["data"]["id"] != network["id"]
    history = (await client.get(path + "/logs")).json()["data"][::-1]
    assert [log["operation"] for log in history] == ["create", "update", "delete"]
    assert history[1]["before"] == history[0]["after"]
    assert history[2]["before"] == history[1]["after"] and history[2]["after"] is None


@pytest.mark.parametrize(
    ("first", "duplicate"),
    [("Korea", " korea "), ("대한민국", normalize("NFD", "대한민국")), ("Straße", "STRASSE")],
)
async def test_unique_name_create_and_update_without_side_effects(client, first, duplicate):
    original = (await client.post("/networks", json={"name": first, "code": "KOR"})).json()["data"]
    response = await client.post("/networks", json={"name": duplicate, "code": "NEW"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NETWORK_NAME_DUPLICATE"
    assert response.json()["error"]["details"][0]["field"] == "body.name"
    other = (await client.post("/networks", json={"name": "Other", "code": "OTH"})).json()["data"]
    path = "/networks/" + other["id"]
    response = await client.patch(path, json={"name": duplicate})
    assert (
        response.status_code == 409 and response.json()["error"]["code"] == "NETWORK_NAME_DUPLICATE"
    )
    assert (await client.get(path)).json()["data"] == other
    assert len((await client.get(path + "/logs")).json()["data"]) == 1
    assert len((await client.get("/networks/" + original["id"] + "/logs")).json()["data"]) == 1
    response = await client.post("/networks", json={"name": "Unique", "code": " kor "})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NETWORK_CODE_DUPLICATE"
    assert response.json()["error"]["details"][0]["field"] == "body.code"


@pytest.mark.parametrize("name", ["ABC\ud800", "ABC\udfff", "A\x00B"])
async def test_unstorable_name_rejected_without_changes(client, name):
    original = (await client.post("/networks", json={"name": "Original", "code": "ORG"})).json()[
        "data"
    ]
    path = "/networks/" + original["id"]
    for method, url, body in [
        ("POST", "/networks", {"name": name, "code": "NEW"}),
        ("PATCH", path, {"name": name}),
    ]:
        response = await client.request(
            method,
            url,
            content=json.dumps(body).encode("ascii"),
            headers={"Content-Type": "application/json"},
        )
        assert (
            response.status_code == 422 and response.json()["error"]["code"] == "VALIDATION_ERROR"
        )
    assert (await client.get(path)).json()["data"] == original
    assert len((await client.get(path + "/logs")).json()["data"]) == 1
    assert len((await client.get("/networks")).json()["data"]) == 1


async def test_pagination_and_cross_dimension_cursor(client):
    ids = []
    for name, code in [("Korea", "KOR"), ("Japan", "JPN"), ("Canada", "CAN")]:
        response = await client.post("/networks", json={"name": name, "code": code})
        ids.append(response.json()["data"]["id"])
    first = (await client.get("/networks", params={"limit": 2})).json()
    cursor = first["meta"]["page"]["next_cursor"]
    second = (await client.get("/networks", params={"cursor": cursor, "limit": 1})).json()
    assert [item["id"] for item in first["data"] + second["data"]] == ids[::-1]
    assert second["meta"]["page"] == {"next_cursor": None, "has_next": False}
    for target in ["/companies", "/models", "/brands", "/countries"]:
        assert (await client.get(target, params={"cursor": cursor})).status_code == 400
        for name, code in [("Korea", "KOR"), ("Japan", "JPN")]:
            assert (await client.post(target, json={"name": name, "code": code})).status_code == 201
        other_cursor = (await client.get(target, params={"limit": 1})).json()["meta"]["page"][
            "next_cursor"
        ]
        assert (await client.get("/networks", params={"cursor": other_cursor})).status_code == 400
    for invalid in ["", "bad", cursor + "x", "a" * 2049]:
        assert (await client.get("/networks", params={"cursor": invalid})).status_code == 400
    for limit in [0, 101, "invalid"]:
        assert (await client.get("/networks", params={"limit": limit})).status_code == 422
    assert (await client.get("/networks/" + str(uuid4()))).status_code == 404
    assert (await client.get("/networks/invalid")).status_code == 422


async def test_auto_generation_collision_and_full_extraction(client):
    created = await client.post("/networks", json={"name": " lte-a "})
    assert created.status_code == 201
    assert (created.json()["data"]["name"], created.json()["data"]["code"]) == ("LTE-A", "LTEA")
    collision = await client.post("/networks", json={"name": "LTE A"})
    assert collision.status_code == 409
    assert collision.json()["error"]["code"] == "DIMENSION_AUTO_CODE_DUPLICATE"
    assert (
        await client.post("/networks", json={"name": "LTE A", "code": "CUSTOM"})
    ).status_code == 201
    assert len((await client.get("/networks")).json()["data"]) == 2
