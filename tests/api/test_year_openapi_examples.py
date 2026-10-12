import pytest
from pydantic import TypeAdapter

from mdm_demo.presentation.schemas.common import ErrorResponse, ListResponse, SuccessResponse
from mdm_demo.presentation.schemas.year import YearResponse
from mdm_demo.presentation.schemas.year_examples import CHANGE_EXAMPLES, CREATE_EXAMPLES
from mdm_demo.presentation.schemas.year_log import YearLogResponse


def body_examples(schema, path, method):
    return schema["paths"][path][method]["requestBody"]["content"]["application/json"]["examples"]


@pytest.mark.parametrize("key", list(CREATE_EXAMPLES))
async def test_create_openapi_examples_are_executable(client, key):
    schema = (await client.get("/openapi.json")).json()
    item = body_examples(schema, "/years", "post")[key]
    if key == "duplicate":
        assert (await client.post("/years", json={"year": 2024})).status_code == 201
    response = await client.post("/years", json=item["value"])
    assert response.status_code == item["x-expected-status"], (key, response.text)


@pytest.mark.parametrize("key", list(CHANGE_EXAMPLES))
async def test_change_openapi_examples_are_executable(client, key):
    schema = (await client.get("/openapi.json")).json()
    item = body_examples(schema, "/years/{year_id}", "patch")[key]
    created = await client.post("/years", json={"year": 2024})
    year = created.json()["data"]
    path = "/years/" + year["id"]
    if key == "duplicate":
        assert (await client.post("/years", json={"year": 2025})).status_code == 201
    response = await client.patch(path, json=item["value"])
    assert response.status_code == item["x-expected-status"], (key, response.text)
    if key == "no_change":
        assert response.json()["data"] == year
        assert len((await client.get(path + "/logs")).json()["data"]) == 1


async def test_openapi_examples_preserve_nulls_and_concrete_response_shapes(client):
    schema = (await client.get("/openapi.json")).json()
    create = body_examples(schema, "/years", "post")
    assert "code" not in create["auto_code"]["value"]
    assert create["float_year"]["value"]["year"] == 2024.5
    assert type(create["float_year"]["value"]["year"]) is float
    assert create["null_code"]["value"]["code"] is None
    years = {
        ("/years", "post"): SuccessResponse[YearResponse],
        ("/years", "get"): ListResponse[YearResponse],
        ("/years/{year_id}", "get"): SuccessResponse[YearResponse],
        ("/years/{year_id}", "patch"): SuccessResponse[YearResponse],
        ("/years/{year_id}/logs", "get"): ListResponse[YearLogResponse],
        ("/year-logs/{log_id}", "get"): SuccessResponse[YearLogResponse],
    }
    for (path, method), year in years.items():
        operation = schema["paths"][path][method]
        success_status = "201" if method == "post" else "200"
        examples = operation["responses"][success_status]["content"]["application/json"]["examples"]
        assert examples
        for item in examples.values():
            TypeAdapter(year).validate_python(item["value"])
        for code, response in operation["responses"].items():
            if int(code) >= 400 and "examples" in response.get("content", {}).get(
                "application/json", {}
            ):
                for item in response["content"]["application/json"]["examples"].values():
                    ErrorResponse.model_validate(item["value"])
        for parameter in operation.get("parameters", []):
            if parameter["name"] in {"year_id", "log_id", "limit"}:
                assert parameter.get("examples")
    for path, method in [("/years/{year_id}", "delete"), ("/health", "get")]:
        assert "content" not in schema["paths"][path][method]["responses"]["204"]
    assert "content" not in schema["paths"]["/years/{year_id}"]["delete"]["responses"]["204"]


async def test_query_examples_and_missing_id_examples(client):
    schema = (await client.get("/openapi.json")).json()
    year_id = (await client.post("/years", json={"year": 2024})).json()["data"]["id"]
    for template, path in [
        ("/years", "/years"),
        ("/years/{year_id}/logs", f"/years/{year_id}/logs"),
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
        ("/years/{year_id}", "year_id", 404),
        ("/years/{year_id}/logs", "year_id", 200),
        ("/year-logs/{log_id}", "log_id", 404),
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


@pytest.mark.parametrize("method", ["post", "patch"])
async def test_integral_float_raw_body_is_rejected_without_changes(client, method):
    created = await client.post("/years", json={"year": 2023})
    original = created.json()["data"]
    path = "/years/" + original["id"]
    before = (await client.get(path + "/logs")).json()["data"]
    response = await client.request(
        method,
        "/years" if method == "post" else path,
        content='{"year":2024.0}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert (await client.get(path)).json()["data"] == original
    assert (await client.get(path + "/logs")).json()["data"] == before
    assert [item["year"] for item in (await client.get("/years")).json()["data"]] == [2023]


@pytest.mark.parametrize("method", ["post", "patch"])
async def test_duplicate_error_matches_openapi_example(client, method):
    schema = (await client.get("/openapi.json")).json()
    created = await client.post("/years", json={"year": 2024})
    path = "/years/" + created.json()["data"]["id"]
    assert (await client.post("/years", json={"year": 2025})).status_code == 201
    response = await client.request(
        method, "/years" if method == "post" else path, json={"year": 2025}
    )
    template = "/years" if method == "post" else "/years/{year_id}"
    example = schema["paths"][template][method]["responses"]["409"]["content"]["application/json"][
        "examples"
    ]["YEAR_DUPLICATE"]["value"]
    assert response.status_code == 409
    assert response.json()["error"] == example["error"]
