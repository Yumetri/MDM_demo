import json
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from mdm_demo.infrastructure.persistence.models.brand import BrandModel
from mdm_demo.infrastructure.persistence.models.brand_log import BrandLogModel


def assert_request_id(response):
    assert UUID(response.headers["x-request-id"])
    if response.status_code != 204:
        assert response.json()["meta"]["request_id"] == response.headers["x-request-id"]


async def test_crud_noop_delete_reuse_and_audit(client, database):
    _, factory = database
    created = await client.post("/brands", json={"name": "  Samsung  "})
    assert created.status_code == 201
    assert_request_id(created)
    brand = created.json()["data"]
    assert brand["name"] == "Samsung" and brand["code"] == "SAM"
    path = f"/brands/{brand['id']}"
    fetched = await client.get(path)
    assert fetched.status_code == 200 and fetched.json()["data"] == brand
    noop = await client.patch(path, json={"name": " Samsung "})
    assert noop.json()["data"] == brand
    renamed = await client.patch(path, json={"name": "삼성전자"})
    assert renamed.status_code == 200
    assert renamed.json()["data"]["code"] == "SAM"
    assert renamed.json()["data"]["name"] == "삼성전자"
    deleted = await client.delete(path)
    assert deleted.status_code == 204 and deleted.content == b""
    assert_request_id(deleted)
    assert (await client.get(path)).status_code == 404
    assert (await client.delete(path)).status_code == 404
    recreated = await client.post("/brands", json={"name": "Samsung"})
    assert recreated.status_code == 201
    assert recreated.json()["data"]["id"] != brand["id"]
    async with factory() as session:
        history = list(
            await session.scalars(
                select(BrandLogModel)
                .where(BrandLogModel.brand_id == UUID(brand["id"]))
                .order_by(BrandLogModel.occurred_at, BrandLogModel.id)
            )
        )
    assert [log.operation for log in history] == ["create", "update", "delete"]
    assert history[0].request_id == UUID(created.headers["x-request-id"])
    assert history[1].request_id == UUID(renamed.headers["x-request-id"])
    assert history[2].request_id == UUID(deleted.headers["x-request-id"])
    assert history[0].before is None
    assert history[1].before == history[0].after
    assert history[2].before == history[1].after and history[2].after is None


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"name": None},
        {"name": 123},
        {"name": " "},
        {"name": "x" * 101},
        {"name": "Test", "code": None},
        {"name": "Test", "code": ""},
        {"name": "Test", "code": " A BC"},
        {"name": "Test", "code": "A-C"},
        {"name": "Test", "code": "ＡＢＣ"},
        {"name": "Test", "code": 123},
        {"name": "Test", "unknown": "secret-input"},
    ],
)
async def test_validation_contract(client, body):
    response = await client.post("/brands", json=body)
    assert response.status_code == 422
    assert_request_id(response)
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "secret-input" not in response.text
    assert all(
        set(detail) == {"field", "code", "message"}
        for detail in response.json()["error"]["details"]
    )


async def test_duplicate_names_manual_normalization_and_error_codes(client):
    first = await client.post("/brands", json={"name": "Same", "code": "abc"})
    assert first.json()["data"]["code"] == "ABC"
    assert (await client.post("/brands", json={"name": "Same", "code": "xyz"})).status_code == 201
    duplicate = await client.post("/brands", json={"name": "Other", "code": "ABC"})
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "BRAND_CODE_DUPLICATE"
    auto_duplicate = await client.post("/brands", json={"name": "ABC Incorporated"})
    assert auto_duplicate.status_code == 409
    assert auto_duplicate.json()["error"]["code"] == "DIMENSION_AUTO_CODE_DUPLICATE"
    unavailable = await client.post("/brands", json={"name": "삼성"})
    assert unavailable.status_code == 422
    assert unavailable.json()["error"]["code"] == "DIMENSION_AUTO_CODE_UNAVAILABLE"
    assert unavailable.json()["error"]["message"] == (
        "brand에서 코드를 자동으로 생성할 수 없습니다. 코드를 직접 입력해 주세요."
    )


async def test_patch_rejects_code_and_empty_body(client):
    created = await client.post("/brands", json={"name": "Samsung"})
    path = "/brands/" + created.json()["data"]["id"]
    for body in [{}, {"name": "New", "code": "NEW"}, {"code": "SAM"}, {"name": None}]:
        response = await client.patch(path, json=body)
        assert response.status_code == 422
    assert (await client.get(path)).json()["data"]["name"] == "Samsung"


async def test_pagination_and_invalid_cursor(client):
    empty = await client.get("/brands")
    assert empty.json()["data"] == []
    assert empty.json()["meta"]["page"] == {"next_cursor": None, "has_next": False}
    ids = []
    for name in ["Alpha", "Bravo", "Charlie"]:
        response = await client.post("/brands", json={"name": name})
        ids.append(response.json()["data"]["id"])
    first = await client.get("/brands", params={"limit": 2})
    cursor = first.json()["meta"]["page"]["next_cursor"]
    second = await client.get("/brands", params={"limit": 1, "cursor": cursor})
    assert [item["id"] for item in first.json()["data"] + second.json()["data"]] == ids
    assert second.json()["meta"]["page"] == {"next_cursor": None, "has_next": False}
    for invalid in ["", "bad", cursor + "x", "a" * 2049]:
        response = await client.get("/brands", params={"cursor": invalid})
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_CURSOR"
    for limit in [0, 101, "invalid"]:
        assert (await client.get("/brands", params={"limit": limit})).status_code == 422
    assert (await client.get("/brands", params={"limit": 100})).status_code == 200


async def test_missing_invalid_id_and_framework_errors(client):
    assert (await client.get(f"/brands/{uuid4()}")).status_code == 404
    assert (await client.get("/brands/invalid")).status_code == 422
    unknown = await client.get("/does-not-exist")
    assert unknown.status_code == 404 and unknown.json()["error"]["code"] == "NOT_FOUND"
    method = await client.put("/brands")
    assert method.status_code == 405 and "allow" in method.headers
    malformed = await client.post(
        "/brands", content="{", headers={"Content-Type": "application/json"}
    )
    assert malformed.status_code == 422
    for response in [unknown, method, malformed]:
        assert_request_id(response)


async def test_unexpected_error_sanitized_and_http_headers_preserved(app_factory):
    app = app_factory()

    @app.get("/test-error")
    async def failure():
        raise RuntimeError("secret SQL password")

    @app.get("/test-auth")
    async def auth_failure():
        raise HTTPException(401, detail="sensitive detail", headers={"WWW-Authenticate": "Bearer"})

    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as client:
            response = await client.get("/test-error")
            assert response.status_code == 500
            assert response.json()["error"]["code"] == "INTERNAL_ERROR"
            assert "secret" not in response.text and "SQL" not in response.text
            assert_request_id(response)
            auth = await client.get("/test-auth")
            assert auth.status_code == 401 and auth.headers["www-authenticate"] == "Bearer"
            assert auth.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_openapi_concrete_contract(client):
    response = await client.get("/openapi.json")
    schema = response.json()
    assert set(schema["paths"]["/brands"]) == {"get", "post"}
    assert set(schema["paths"]["/brands/{brand_id}"]) == {"get", "patch", "delete"}
    create = schema["components"]["schemas"]["CreateBrand"]
    assert create["required"] == ["name"]
    assert create["properties"]["code"]["type"] == "string"
    assert create["additionalProperties"] is False
    assert "content" not in schema["paths"]["/brands/{brand_id}"]["delete"]["responses"]["204"]
    for status in ["409", "422", "500"]:
        assert (
            "ErrorResponse"
            in schema["paths"]["/brands"]["post"]["responses"][status]["content"][
                "application/json"
            ]["schema"]["$ref"]
        )


async def test_validation_failure_writes_nothing(client, database):
    _, factory = database
    await client.post("/brands", json={"name": "LG"})
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(BrandLogModel)) == 0


@pytest.mark.parametrize("name", ["ABC\ud800", "ABC\udfff"])
async def test_unencodable_name_rejected_without_brand_or_log_changes(client, database, name):
    _, factory = database
    created = await client.post("/brands", json={"name": "Original", "code": "ORG"})
    assert created.status_code == 201
    original = created.json()["data"]
    path = "/brands/" + original["id"]
    for method, url, body in [
        ("POST", "/brands", {"name": name, "code": "NEW"}),
        ("POST", "/brands", {"name": name}),
        ("PATCH", path, {"name": name}),
    ]:
        # Send JSON escapes: HTTPX's json= encoding cannot represent lone surrogates.
        response = await client.request(
            method,
            url,
            content=json.dumps(body).encode("ascii"),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422
        assert_request_id(response)
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
        assert response.json()["error"]["details"][0]["field"] == "body.name"
        assert (await client.get(path)).json()["data"] == original
        async with factory() as session:
            assert await session.scalar(select(func.count()).select_from(BrandModel)) == 1
            history = list(await session.scalars(select(BrandLogModel)))
            assert len(history) == 1
            assert history[0].operation == "create"
            assert history[0].after == {
                "id": original["id"],
                "name": original["name"],
                "code": original["code"],
            }


@pytest.mark.parametrize("escaped", [False, True])
async def test_valid_unicode_name_round_trips(client, escaped):
    name = "삼성🙂"
    body = json.dumps({"name": name, "code": "SAM"}, ensure_ascii=escaped)
    created = await client.post(
        "/brands", content=body.encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    assert created.status_code == 201
    assert created.json()["data"]["name"] == name
    path = "/brands/" + created.json()["data"]["id"]
    renamed = await client.patch(
        path,
        content=json.dumps({"name": name + "전자"}, ensure_ascii=escaped).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    assert renamed.status_code == 200
    assert (await client.get(path)).json()["data"]["name"] == name + "전자"


async def test_independent_dimensions_and_cursor_isolation(client):
    for path in ("/companies", "/brands"):
        for code in ("AAA", "BBB"):
            assert (await client.post(path, json={"name": "Same", "code": code})).status_code == 201
    company_page = (await client.get("/companies", params={"limit": 1})).json()
    brand_page = (await client.get("/brands", params={"limit": 1})).json()
    for target, source in [("/brands", company_page), ("/companies", brand_page)]:
        response = await client.get(
            target, params={"cursor": source["meta"]["page"]["next_cursor"]}
        )
        assert response.status_code == 400
    company_id = company_page["data"][0]["id"]
    brand_id = brand_page["data"][0]["id"]
    await client.patch(f"/companies/{company_id}", json={"name": "Changed"})
    history = (await client.get(f"/companies/{company_id}/logs", params={"limit": 1})).json()
    response = await client.get(
        f"/brands/{brand_id}/logs", params={"cursor": history["meta"]["page"]["next_cursor"]}
    )
    assert response.status_code == 400
    await client.delete(f"/companies/{company_id}")
    assert (await client.get(f"/brands/{brand_id}")).status_code == 200


async def test_trimmed_numeric_code_duplicate_and_name_boundary(client):
    created = await client.post("/brands", json={"name": "갤럭시 S24"})
    assert created.status_code == 201 and created.json()["data"]["code"] == "S24"
    duplicate = await client.post("/brands", json={"name": "Other", "code": " s24 "})
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "BRAND_CODE_DUPLICATE"
    assert (
        await client.post("/brands", json={"name": "가" * 100, "code": "100"})
    ).status_code == 201
    assert (
        await client.post("/brands", json={"name": "가" * 101, "code": "101"})
    ).status_code == 422


async def test_all_dimension_cursors_are_isolated_and_codes_are_independent(client):
    tokens = {}
    for collection in ("companies", "models", "brands"):
        for name in ("Alpha", "Bravo"):
            response = await client.post("/" + collection, json={"name": name})
            assert response.status_code == 201
        first = (await client.get("/" + collection, params={"limit": 1})).json()
        tokens["/" + collection] = first["meta"]["page"]["next_cursor"]
        identifier = first["data"][0]["id"]
        assert (
            await client.patch(f"/{collection}/{identifier}", json={"name": "Changed"})
        ).status_code == 200
        path = f"/{collection}/{identifier}/logs"
        history = (await client.get(path, params={"limit": 1})).json()
        tokens[path] = history["meta"]["page"]["next_cursor"]
    for source, token in tokens.items():
        assert token
        for target in tokens:
            response = await client.get(target, params={"cursor": token})
            if source == target:
                assert response.status_code == 200
            else:
                assert response.status_code == 400
                assert response.json()["error"]["code"] == "INVALID_CURSOR"
