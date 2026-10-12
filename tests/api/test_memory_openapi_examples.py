import json

import pytest
from pydantic import TypeAdapter

from mdm_demo.presentation.schemas.common import ErrorResponse, ListResponse, SuccessResponse
from mdm_demo.presentation.schemas.memory import MemoryResponse
from mdm_demo.presentation.schemas.memory_examples import CHANGE_EXAMPLES, CREATE_EXAMPLES
from mdm_demo.presentation.schemas.memory_log import MemoryLogResponse


def examples(schema, path, method):
    return schema["paths"][path][method]["requestBody"]["content"]["application/json"]["examples"]


@pytest.mark.parametrize("key", list(CREATE_EXAMPLES))
async def test_create_examples_from_openapi_execute(client, key):
    schema = (await client.get("/openapi.json")).json()
    item = examples(schema, "/memories", "post")[key]
    if key.startswith("duplicate_"):
        setup = (
            {"capacity": 1, "unit": "TB"}
            if key == "duplicate_equivalent"
            else {"capacity": 256, "unit": "GB"}
        )
        assert (await client.post("/memories", json=setup)).status_code == 201
    response = await client.post(
        "/memories", content=json.dumps(item["value"]), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == item["x-expected-status"], (key, response.text)
    if response.status_code >= 400:
        assert response.json()["error"]["code"] == (
            "MEMORY_CAPACITY_DUPLICATE" if response.status_code == 409 else "VALIDATION_ERROR"
        )


@pytest.mark.parametrize("key", list(CHANGE_EXAMPLES))
async def test_change_examples_from_openapi_execute_and_preserve_rejected_state(client, key):
    schema = (await client.get("/openapi.json")).json()
    item = examples(schema, "/memories/{memory_id}", "patch")[key]
    setup = (
        {"capacity": 1, "unit": "TB"}
        if key == "equivalent_representation"
        else {"capacity": 256, "unit": "GB"}
    )
    original = (await client.post("/memories", json=setup)).json()["data"]
    if key in {"duplicate_update", "duplicate_equivalent_update"}:
        other = (
            {"capacity": 512, "unit": "GB"}
            if key == "duplicate_update"
            else {"capacity": 1, "unit": "TB"}
        )
        assert (await client.post("/memories", json=other)).status_code == 201
    path = f"/memories/{original['id']}"
    response = await client.patch(
        path, content=json.dumps(item["value"]), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == item["x-expected-status"], (key, response.text)
    if response.status_code >= 400 or key == "no_change":
        assert (await client.get(path)).json()["data"] == original
        assert len((await client.get(path + "/logs")).json()["data"]) == 1
    else:
        assert len((await client.get(path + "/logs")).json()["data"]) == 2


async def test_schemas_examples_integer_nulls_errors_and_204(client):
    schema = (await client.get("/openapi.json")).json()
    create = examples(schema, "/memories", "post")
    assert create["null_body"]["value"] is None
    assert create["null_code"]["value"]["code"] is None
    models = {
        ("/memories", "post"): SuccessResponse[MemoryResponse],
        ("/memories", "get"): ListResponse[MemoryResponse],
        ("/memories/{memory_id}", "get"): SuccessResponse[MemoryResponse],
        ("/memories/{memory_id}", "patch"): SuccessResponse[MemoryResponse],
        ("/memories/{memory_id}/logs", "get"): ListResponse[MemoryLogResponse],
        ("/memory-logs/{log_id}", "get"): SuccessResponse[MemoryLogResponse],
    }
    for (path, method), model in models.items():
        operation = schema["paths"][path][method]
        status = "201" if method == "post" else "200"
        for item in operation["responses"][status]["content"]["application/json"][
            "examples"
        ].values():
            TypeAdapter(model).validate_python(item["value"])
        for status, response in operation["responses"].items():
            if int(status) >= 400:
                for item in (
                    response.get("content", {})
                    .get("application/json", {})
                    .get("examples", {})
                    .values()
                ):
                    ErrorResponse.model_validate(item["value"])
    for method in ["post", "patch"]:
        operation = schema["paths"]["/memories" if method == "post" else "/memories/{memory_id}"][
            method
        ]
        duplicate = operation["responses"]["409"]["content"]["application/json"]["examples"][
            "MEMORY_CAPACITY_DUPLICATE"
        ]["value"]
        assert duplicate["error"]["details"][0]["field"] == "body.capacity"
        reference = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].split(
            "/"
        )[-1]
        request = schema["components"]["schemas"][reference]
        assert set(request["required"]) == {"capacity", "unit"}
        assert set(request["properties"]) == {"capacity", "unit"}
        assert request["properties"]["capacity"]["type"] == "integer"
        assert request["additionalProperties"] is False
    assert "content" not in schema["paths"]["/memories/{memory_id}"]["delete"]["responses"]["204"]


async def test_path_query_examples_and_cursor_default(client):
    schema = (await client.get("/openapi.json")).json()
    created = (await client.post("/memories", json={"capacity": 256, "unit": "GB"})).json()["data"]
    for template, path in [
        ("/memories", "/memories"),
        ("/memories/{memory_id}/logs", f"/memories/{created['id']}/logs"),
    ]:
        params = {p["name"]: p for p in schema["paths"][template]["get"]["parameters"]}
        cursor = params["cursor"]
        assert not cursor["required"]
        for location in [cursor, cursor["schema"]]:
            assert "example" not in location and "examples" not in location
            assert location.get("default") is None
        assert (await client.get(path)).status_code == 200
        for key, item in params["limit"]["examples"].items():
            response = await client.get(path, params={"limit": item["value"]})
            assert response.status_code == (
                422 if key in {"zero", "too_large", "wrong_type"} else 200
            )
    for template, name in [
        ("/memories/{memory_id}", "memory_id"),
        ("/memories/{memory_id}/logs", "memory_id"),
        ("/memory-logs/{log_id}", "log_id"),
    ]:
        parameter = next(
            p for p in schema["paths"][template]["get"]["parameters"] if p["name"] == name
        )
        for key in ["missing", "invalid"]:
            item = parameter["examples"][key]
            response = await client.get(template.replace("{" + name + "}", item["value"]))
            assert response.status_code == item["x-expected-status"]


@pytest.mark.parametrize("method", ["post", "patch"])
async def test_raw_integral_float_is_rejected_without_mutating_data_or_history(client, method):
    original = (await client.post("/memories", json={"capacity": 512, "unit": "GB"})).json()["data"]
    path = f"/memories/{original['id']}"
    before_list = (await client.get("/memories")).json()["data"]
    before_logs = (await client.get(path + "/logs")).json()["data"]

    response = await client.request(
        method,
        "/memories" if method == "post" else path,
        content='{"capacity":256.0,"unit":"GB"}',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"][0]["field"] == "body.capacity"
    assert (await client.get("/memories")).json()["data"] == before_list
    assert (await client.get(path)).json()["data"] == original
    assert (await client.get(path + "/logs")).json()["data"] == before_logs
