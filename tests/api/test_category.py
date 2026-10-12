import json
from unicodedata import normalize
from uuid import uuid4

import pytest


async def test_crud_normalization_noop_delete_reuse(client):
    created = await client.post("/categories", json={"name": " smartphone ", "code": " sma "})
    assert created.status_code == 201
    category = created.json()["data"]
    assert (category["name"], category["code"]) == ("SMARTPHONE", "SMA")
    path = "/categories/" + category["id"]
    assert (await client.get(path)).json()["data"] == category
    assert (await client.patch(path, json={"name": " Smartphone "})).json()["data"] == category
    assert len((await client.get(path + "/logs")).json()["data"]) == 1
    updated = await client.patch(path, json={"name": "스마트폰"})
    assert updated.status_code == 200 and updated.json()["data"]["code"] == "SMA"
    assert (await client.patch(path, json={"name": normalize("NFD", "스마트폰")})).json()[
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
    replacement = await client.post("/categories", json={"name": "스마트폰", "code": "SMA"})
    assert replacement.status_code == 201 and replacement.json()["data"]["id"] != category["id"]
    history = (await client.get(path + "/logs")).json()["data"]
    assert [log["operation"] for log in history] == ["create", "update", "delete"]
    assert history[1]["before"] == history[0]["after"]
    assert history[2]["before"] == history[1]["after"] and history[2]["after"] is None


@pytest.mark.parametrize(
    ("first", "duplicate"),
    [
        ("Smartphone", " smartphone "),
        ("스마트폰", normalize("NFD", "스마트폰")),
        ("Straße", "STRASSE"),
    ],
)
async def test_unique_name_create_and_update_without_side_effects(client, first, duplicate):
    original = (await client.post("/categories", json={"name": first, "code": "SMA"})).json()[
        "data"
    ]
    response = await client.post("/categories", json={"name": duplicate, "code": "NEW"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CATEGORY_NAME_DUPLICATE"
    assert response.json()["error"]["details"][0]["field"] == "body.name"
    other = (await client.post("/categories", json={"name": "Other", "code": "OTH"})).json()["data"]
    path = "/categories/" + other["id"]
    response = await client.patch(path, json={"name": duplicate})
    assert (
        response.status_code == 409
        and response.json()["error"]["code"] == "CATEGORY_NAME_DUPLICATE"
    )
    assert (await client.get(path)).json()["data"] == other
    assert len((await client.get(path + "/logs")).json()["data"]) == 1
    assert len((await client.get("/categories/" + original["id"] + "/logs")).json()["data"]) == 1
    response = await client.post("/categories", json={"name": "Unique", "code": " sma "})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CATEGORY_CODE_DUPLICATE"
    assert response.json()["error"]["details"][0]["field"] == "body.code"


@pytest.mark.parametrize("name", ["ABC\ud800", "ABC\udfff", "A\x00B"])
async def test_unstorable_name_rejected_without_changes(client, name):
    original = (await client.post("/categories", json={"name": "Original", "code": "ORG"})).json()[
        "data"
    ]
    path = "/categories/" + original["id"]
    for method, url, body in [
        ("POST", "/categories", {"name": name, "code": "NEW"}),
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
    assert len((await client.get("/categories")).json()["data"]) == 1


async def test_pagination_and_cross_dimension_cursor(client):
    ids = []
    for name, code in [("Smartphone", "SMA"), ("Tablet", "TAB"), ("Canada", "CAN")]:
        response = await client.post("/categories", json={"name": name, "code": code})
        ids.append(response.json()["data"]["id"])
    first = (await client.get("/categories", params={"limit": 2})).json()
    cursor = first["meta"]["page"]["next_cursor"]
    second = (await client.get("/categories", params={"cursor": cursor, "limit": 1})).json()
    assert [item["id"] for item in first["data"] + second["data"]] == ids
    assert second["meta"]["page"] == {"next_cursor": None, "has_next": False}
    for target in ["/companies", "/models"]:
        assert (await client.get(target, params={"cursor": cursor})).status_code == 400
        for name, code in [("Smartphone", "SMA"), ("Tablet", "TAB")]:
            assert (await client.post(target, json={"name": name, "code": code})).status_code == 201
        other_cursor = (await client.get(target, params={"limit": 1})).json()["meta"]["page"][
            "next_cursor"
        ]
        assert (await client.get("/categories", params={"cursor": other_cursor})).status_code == 400
    for invalid in ["", "bad", cursor + "x", "a" * 2049]:
        assert (await client.get("/categories", params={"cursor": invalid})).status_code == 400
    for limit in [0, 101, "invalid"]:
        assert (await client.get("/categories", params={"limit": limit})).status_code == 422
    assert (await client.get("/categories/" + str(uuid4()))).status_code == 404
    assert (await client.get("/categories/invalid")).status_code == 422


async def test_auto_manual_code_errors_and_strict_updates(client):
    created = await client.post("/categories", json={"name": "Smartphone"})
    assert created.status_code == 201
    category = created.json()["data"]
    assert (category["name"], category["code"]) == ("SMARTPHONE", "SMA")
    for body, status, code in [
        ({"name": "Smartwatch"}, 409, "DIMENSION_AUTO_CODE_DUPLICATE"),
        ({"name": "Other", "code": "sma"}, 409, "CATEGORY_CODE_DUPLICATE"),
        ({"name": "smartphone", "code": "NEW"}, 409, "CATEGORY_NAME_DUPLICATE"),
        ({"name": "스마트폰"}, 422, "DIMENSION_AUTO_CODE_UNAVAILABLE"),
        ({"name": "New", "code": None}, 422, "VALIDATION_ERROR"),
    ]:
        result = await client.post("/categories", json=body)
        assert result.status_code == status and result.json()["error"]["code"] == code
    numeric = await client.post("/categories", json={"name": "Notebook", "code": " n01 "})
    assert numeric.status_code == 201 and numeric.json()["data"]["code"] == "N01"
    for body in [{}, {"name": "New", "code": "NEW"}, {"name": "New", "extra": True}]:
        assert (await client.patch("/categories/" + category["id"], json=body)).status_code == 422
    assert len((await client.get("/categories/" + category["id"] + "/logs")).json()["data"]) == 1


async def test_both_duplicate_has_no_guaranteed_priority(client):
    assert (await client.post("/categories", json={"name": "Smartphone"})).status_code == 201
    response = await client.post("/categories", json={"name": " smartphone "})
    assert response.status_code == 409
    assert response.json()["error"]["code"] in {
        "CATEGORY_NAME_DUPLICATE",
        "DIMENSION_AUTO_CODE_DUPLICATE",
    }
