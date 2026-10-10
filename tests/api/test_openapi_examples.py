import pytest
from pydantic import TypeAdapter

from mdm_demo.presentation.schemas.common import ErrorResponse, ListResponse, SuccessResponse
from mdm_demo.presentation.schemas.company import CompanyResponse
from mdm_demo.presentation.schemas.company_log import CompanyLogResponse
from mdm_demo.presentation.schemas.examples import CREATE_EXAMPLES, RENAME_EXAMPLES


def body_examples(schema, path, method):
    return schema["paths"][path][method]["requestBody"]["content"]["application/json"]["examples"]


@pytest.mark.parametrize("key", list(CREATE_EXAMPLES))
async def test_create_openapi_examples_are_executable(client, key):
    schema = (await client.get("/openapi.json")).json()
    item = body_examples(schema, "/companies", "post")[key]
    if key.startswith("duplicate_"):
        assert (await client.post("/companies", json={"name": "Samsung"})).status_code == 201
    response = await client.post("/companies", json=item["value"])
    assert response.status_code == item["x-expected-status"], (key, response.text)


@pytest.mark.parametrize("key", list(RENAME_EXAMPLES))
async def test_rename_openapi_examples_are_executable(client, key):
    schema = (await client.get("/openapi.json")).json()
    item = body_examples(schema, "/companies/{company_id}", "patch")[key]
    created = await client.post("/companies", json={"name": "Samsung"})
    company = created.json()["data"]
    path = "/companies/" + company["id"]
    response = await client.patch(path, json=item["value"])
    assert response.status_code == item["x-expected-status"], (key, response.text)
    if key == "no_change":
        assert response.json()["data"] == company
        assert len((await client.get(path + "/logs")).json()["data"]) == 1


async def test_openapi_examples_preserve_nulls_and_concrete_response_shapes(client):
    schema = (await client.get("/openapi.json")).json()
    create = body_examples(schema, "/companies", "post")
    assert "code" not in create["auto_code"]["value"]
    assert create["null_code"]["value"]["code"] is None
    models = {
        ("/companies", "post"): SuccessResponse[CompanyResponse],
        ("/companies", "get"): ListResponse[CompanyResponse],
        ("/companies/{company_id}", "get"): SuccessResponse[CompanyResponse],
        ("/companies/{company_id}", "patch"): SuccessResponse[CompanyResponse],
        ("/companies/{company_id}/logs", "get"): ListResponse[CompanyLogResponse],
        ("/company-logs/{log_id}", "get"): SuccessResponse[CompanyLogResponse],
    }
    for (path, method), model in models.items():
        operation = schema["paths"][path][method]
        success_status = "201" if method == "post" else "200"
        examples = operation["responses"][success_status]["content"]["application/json"]["examples"]
        assert examples
        for item in examples.values():
            TypeAdapter(model).validate_python(item["value"])
        for code, response in operation["responses"].items():
            if int(code) >= 400 and "examples" in response.get("content", {}).get(
                "application/json", {}
            ):
                for item in response["content"]["application/json"]["examples"].values():
                    ErrorResponse.model_validate(item["value"])
        for parameter in operation.get("parameters", []):
            if parameter["name"] in {"company_id", "log_id", "limit"}:
                assert parameter.get("examples")
    for path, method in [("/companies/{company_id}", "delete"), ("/health", "get")]:
        assert "content" not in schema["paths"][path][method]["responses"]["204"]
    assert "content" not in schema["paths"]["/companies/{company_id}"]["delete"]["responses"]["204"]


async def test_query_examples_and_missing_id_examples(client):
    schema = (await client.get("/openapi.json")).json()
    company_id = (await client.post("/companies", json={"name": "Samsung"})).json()["data"]["id"]
    for template, path in [
        ("/companies", "/companies"),
        ("/companies/{company_id}/logs", f"/companies/{company_id}/logs"),
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
        ("/companies/{company_id}", "company_id", 404),
        ("/companies/{company_id}/logs", "company_id", 200),
        ("/company-logs/{log_id}", "log_id", 404),
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
