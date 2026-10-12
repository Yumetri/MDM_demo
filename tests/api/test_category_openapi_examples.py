import pytest
from pydantic import TypeAdapter

from mdm_demo.presentation.schemas.category import CategoryResponse
from mdm_demo.presentation.schemas.category_examples import CREATE_EXAMPLES, RENAME_EXAMPLES
from mdm_demo.presentation.schemas.category_log import CategoryLogResponse
from mdm_demo.presentation.schemas.common import ErrorResponse, ListResponse, SuccessResponse


def body_examples(schema, path, method):
    return schema["paths"][path][method]["requestBody"]["content"]["application/json"]["examples"]


@pytest.mark.parametrize("key", list(CREATE_EXAMPLES))
async def test_create_openapi_examples_are_executable(client, key):
    schema = (await client.get("/openapi.json")).json()
    item = body_examples(schema, "/categories", "post")[key]
    if key.startswith("duplicate_"):
        assert (
            await client.post("/categories", json={"name": "SMARTPHONE", "code": "SMA"})
        ).status_code == 201
    response = await client.post("/categories", json=item["value"])
    assert response.status_code == item["x-expected-status"], (key, response.text)
    if key.startswith("duplicate_"):
        expected = {
            "duplicate_name": "CATEGORY_NAME_DUPLICATE",
            "duplicate_code": "CATEGORY_CODE_DUPLICATE",
            "duplicate_auto": "DIMENSION_AUTO_CODE_DUPLICATE",
        }[key]
        assert response.json()["error"]["code"] == expected


@pytest.mark.parametrize("key", list(RENAME_EXAMPLES))
async def test_rename_openapi_examples_are_executable(client, key):
    schema = (await client.get("/openapi.json")).json()
    item = body_examples(schema, "/categories/{category_id}", "patch")[key]
    created = await client.post("/categories", json={"name": "SMARTPHONE", "code": "SMA"})
    category = created.json()["data"]
    path = "/categories/" + category["id"]
    if key == "duplicate_name":
        assert (
            await client.post("/categories", json={"name": "Tablet", "code": "TAB"})
        ).status_code == 201
    response = await client.patch(path, json=item["value"])
    assert response.status_code == item["x-expected-status"], (key, response.text)
    if key == "no_change":
        assert response.json()["data"] == category
        assert len((await client.get(path + "/logs")).json()["data"]) == 1


async def test_openapi_examples_preserve_nulls_and_concrete_response_shapes(client):
    schema = (await client.get("/openapi.json")).json()
    create = body_examples(schema, "/categories", "post")
    assert "code" not in create["auto_code"]["value"]
    assert set(schema["components"]["schemas"]["CreateCategory"]["required"]) == {"name"}
    assert create["null_code"]["value"]["code"] is None
    assert (
        schema["components"]["schemas"]["CreateCategory"]["properties"]["code"]["type"] == "string"
    )
    categories = {
        ("/categories", "post"): SuccessResponse[CategoryResponse],
        ("/categories", "get"): ListResponse[CategoryResponse],
        ("/categories/{category_id}", "get"): SuccessResponse[CategoryResponse],
        ("/categories/{category_id}", "patch"): SuccessResponse[CategoryResponse],
        ("/categories/{category_id}/logs", "get"): ListResponse[CategoryLogResponse],
        ("/category-logs/{log_id}", "get"): SuccessResponse[CategoryLogResponse],
    }
    for (path, method), category in categories.items():
        operation = schema["paths"][path][method]
        success_status = "201" if method == "post" else "200"
        examples = operation["responses"][success_status]["content"]["application/json"]["examples"]
        assert examples
        for item in examples.values():
            TypeAdapter(category).validate_python(item["value"])
        for code, response in operation["responses"].items():
            if int(code) >= 400 and "examples" in response.get("content", {}).get(
                "application/json", {}
            ):
                for item in response["content"]["application/json"]["examples"].values():
                    ErrorResponse.model_validate(item["value"])
        for parameter in operation.get("parameters", []):
            if parameter["name"] in {"category_id", "log_id", "limit"}:
                assert parameter.get("examples")
    for path, method in [("/categories/{category_id}", "delete"), ("/health", "get")]:
        assert "content" not in schema["paths"][path][method]["responses"]["204"]
    assert (
        "content" not in schema["paths"]["/categories/{category_id}"]["delete"]["responses"]["204"]
    )


async def test_query_examples_and_missing_id_examples(client):
    schema = (await client.get("/openapi.json")).json()
    category_id = (
        await client.post("/categories", json={"name": "SMARTPHONE", "code": "SMA"})
    ).json()["data"]["id"]
    for template, path in [
        ("/categories", "/categories"),
        ("/categories/{category_id}/logs", f"/categories/{category_id}/logs"),
    ]:
        parameters = {p["name"]: p for p in schema["paths"][template]["get"]["parameters"]}
        for key, example in parameters["limit"]["examples"].items():
            response = await client.get(path, params={"limit": example["value"]})
            assert response.status_code == (
                422 if key in {"zero", "too_large", "wrong_type"} else 200
            )
        cursor = parameters["cursor"]
        assert cursor["required"] is False
        assert "examples" not in cursor and "example" not in cursor
        assert "examples" not in cursor["schema"] and "example" not in cursor["schema"]
        assert cursor["schema"].get("default") is None
        assert (await client.get(path)).status_code == 200
        for invalid in ("not-a-cursor", ""):
            assert "cursor=" + invalid in cursor["description"]
            response = await client.get(path, params={"cursor": invalid})
            assert response.status_code == 400
    for template, name, expected in [
        ("/categories/{category_id}", "category_id", 404),
        ("/categories/{category_id}/logs", "category_id", 200),
        ("/category-logs/{log_id}", "log_id", 404),
    ]:
        parameter = next(
            p for p in schema["paths"][template]["get"]["parameters"] if p["name"] == name
        )
        examples = parameter["examples"]
        assert (
            await client.get(template.replace("{" + name + "}", examples["missing"]["value"]))
        ).status_code == expected
        assert (
            await client.get(template.replace("{" + name + "}", examples["invalid"]["value"]))
        ).status_code == 422
