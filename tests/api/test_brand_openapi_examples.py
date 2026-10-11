import pytest
from pydantic import TypeAdapter

from mdm_demo.presentation.schemas.brand import BrandResponse
from mdm_demo.presentation.schemas.brand_examples import CREATE_EXAMPLES, RENAME_EXAMPLES
from mdm_demo.presentation.schemas.brand_log import BrandLogResponse
from mdm_demo.presentation.schemas.common import ErrorResponse, ListResponse, SuccessResponse


def body_examples(schema, path, method):
    return schema["paths"][path][method]["requestBody"]["content"]["application/json"]["examples"]


@pytest.mark.parametrize("key", list(CREATE_EXAMPLES))
async def test_create_openapi_examples_are_executable(client, key):
    schema = (await client.get("/openapi.json")).json()
    item = body_examples(schema, "/brands", "post")[key]
    if key.startswith("duplicate_"):
        assert (await client.post("/brands", json={"name": "Galaxy"})).status_code == 201
    response = await client.post("/brands", json=item["value"])
    assert response.status_code == item["x-expected-status"], (key, response.text)


@pytest.mark.parametrize("key", list(RENAME_EXAMPLES))
async def test_rename_openapi_examples_are_executable(client, key):
    schema = (await client.get("/openapi.json")).json()
    item = body_examples(schema, "/brands/{brand_id}", "patch")[key]
    created = await client.post("/brands", json={"name": "Galaxy"})
    brand = created.json()["data"]
    path = "/brands/" + brand["id"]
    response = await client.patch(path, json=item["value"])
    assert response.status_code == item["x-expected-status"], (key, response.text)
    if key == "no_change":
        assert response.json()["data"] == brand
        assert len((await client.get(path + "/logs")).json()["data"]) == 1


async def test_openapi_examples_preserve_nulls_and_concrete_response_shapes(client):
    schema = (await client.get("/openapi.json")).json()
    create = body_examples(schema, "/brands", "post")
    assert "code" not in create["auto_code"]["value"]
    assert create["null_code"]["value"]["code"] is None
    brands = {
        ("/brands", "post"): SuccessResponse[BrandResponse],
        ("/brands", "get"): ListResponse[BrandResponse],
        ("/brands/{brand_id}", "get"): SuccessResponse[BrandResponse],
        ("/brands/{brand_id}", "patch"): SuccessResponse[BrandResponse],
        ("/brands/{brand_id}/logs", "get"): ListResponse[BrandLogResponse],
        ("/brand-logs/{log_id}", "get"): SuccessResponse[BrandLogResponse],
    }
    for (path, method), brand in brands.items():
        operation = schema["paths"][path][method]
        success_status = "201" if method == "post" else "200"
        examples = operation["responses"][success_status]["content"]["application/json"]["examples"]
        assert examples
        for item in examples.values():
            TypeAdapter(brand).validate_python(item["value"])
        for code, response in operation["responses"].items():
            if int(code) >= 400 and "examples" in response.get("content", {}).get(
                "application/json", {}
            ):
                for item in response["content"]["application/json"]["examples"].values():
                    ErrorResponse.model_validate(item["value"])
        for parameter in operation.get("parameters", []):
            if parameter["name"] in {"brand_id", "log_id", "limit"}:
                assert parameter.get("examples")
    for path, method in [("/brands/{brand_id}", "delete"), ("/health", "get")]:
        assert "content" not in schema["paths"][path][method]["responses"]["204"]
    assert "content" not in schema["paths"]["/brands/{brand_id}"]["delete"]["responses"]["204"]


async def test_query_examples_and_missing_id_examples(client):
    schema = (await client.get("/openapi.json")).json()
    brand_id = (await client.post("/brands", json={"name": "Galaxy"})).json()["data"]["id"]
    for template, path in [
        ("/brands", "/brands"),
        ("/brands/{brand_id}/logs", f"/brands/{brand_id}/logs"),
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
        ("/brands/{brand_id}", "brand_id", 404),
        ("/brands/{brand_id}/logs", "brand_id", 200),
        ("/brand-logs/{log_id}", "log_id", 404),
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
