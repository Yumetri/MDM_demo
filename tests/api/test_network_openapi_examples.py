import pytest
from pydantic import TypeAdapter

from mdm_demo.presentation.schemas.common import ErrorResponse, ListResponse, SuccessResponse
from mdm_demo.presentation.schemas.network import NetworkResponse
from mdm_demo.presentation.schemas.network_examples import CREATE_EXAMPLES, RENAME_EXAMPLES
from mdm_demo.presentation.schemas.network_log import NetworkLogResponse


def body_examples(schema, path, method):
    return schema["paths"][path][method]["requestBody"]["content"]["application/json"]["examples"]


@pytest.mark.parametrize("key", list(CREATE_EXAMPLES))
async def test_create_openapi_examples_are_executable(client, key):
    schema = (await client.get("/openapi.json")).json()
    item = body_examples(schema, "/networks", "post")[key]
    if key.startswith("duplicate_"):
        assert (await client.post("/networks", json={"name": "LTE"})).status_code == 201
    response = await client.post("/networks", json=item["value"])
    assert response.status_code == item["x-expected-status"], (key, response.text)


@pytest.mark.parametrize("key", list(RENAME_EXAMPLES))
async def test_rename_openapi_examples_are_executable(client, key):
    schema = (await client.get("/openapi.json")).json()
    item = body_examples(schema, "/networks/{network_id}", "patch")[key]
    created = await client.post("/networks", json={"name": "LTE"})
    network = created.json()["data"]
    path = "/networks/" + network["id"]
    if key == "duplicate_name":
        assert (await client.post("/networks", json={"name": "5G"})).status_code == 201
    response = await client.patch(path, json=item["value"])
    assert response.status_code == item["x-expected-status"], (key, response.text)
    if key == "no_change":
        assert response.json()["data"] == network
        assert len((await client.get(path + "/logs")).json()["data"]) == 1


async def test_openapi_examples_preserve_nulls_and_concrete_response_shapes(client):
    schema = (await client.get("/openapi.json")).json()
    create = body_examples(schema, "/networks", "post")
    assert "code" not in create["auto_code"]["value"]
    assert set(schema["components"]["schemas"]["CreateNetwork"]["required"]) == {"name"}
    assert create["null_code"]["value"]["code"] is None
    networks = {
        ("/networks", "post"): SuccessResponse[NetworkResponse],
        ("/networks", "get"): ListResponse[NetworkResponse],
        ("/networks/{network_id}", "get"): SuccessResponse[NetworkResponse],
        ("/networks/{network_id}", "patch"): SuccessResponse[NetworkResponse],
        ("/networks/{network_id}/logs", "get"): ListResponse[NetworkLogResponse],
        ("/network-logs/{log_id}", "get"): SuccessResponse[NetworkLogResponse],
    }
    for (path, method), network in networks.items():
        operation = schema["paths"][path][method]
        success_status = "201" if method == "post" else "200"
        examples = operation["responses"][success_status]["content"]["application/json"]["examples"]
        assert examples
        for item in examples.values():
            TypeAdapter(network).validate_python(item["value"])
        for code, response in operation["responses"].items():
            if int(code) >= 400 and "examples" in response.get("content", {}).get(
                "application/json", {}
            ):
                for item in response["content"]["application/json"]["examples"].values():
                    ErrorResponse.model_validate(item["value"])
        for parameter in operation.get("parameters", []):
            if parameter["name"] in {"network_id", "log_id", "limit"}:
                assert parameter.get("examples")
    for path, method in [("/networks/{network_id}", "delete"), ("/health", "get")]:
        assert "content" not in schema["paths"][path][method]["responses"]["204"]
    assert "content" not in schema["paths"]["/networks/{network_id}"]["delete"]["responses"]["204"]


async def test_query_examples_and_missing_id_examples(client):
    schema = (await client.get("/openapi.json")).json()
    network_id = (await client.post("/networks", json={"name": "LTE"})).json()["data"]["id"]
    for template, path in [
        ("/networks", "/networks"),
        ("/networks/{network_id}/logs", f"/networks/{network_id}/logs"),
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
        ("/networks/{network_id}", "network_id", 404),
        ("/networks/{network_id}/logs", "network_id", 200),
        ("/network-logs/{log_id}", "log_id", 404),
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


async def test_network_schema_and_common_workflow_describe_actual_contract(client):
    schema = (await client.get("/openapi.json")).json()
    request = schema["components"]["schemas"]["CreateNetwork"]
    assert request["required"] == ["name"]
    assert request["properties"]["code"]["type"] == "string"
    assert "1~20자" in request["properties"]["code"]["description"]
    assert "Network 테스트 준비" in schema["info"]["description"]
    assert schema["info"]["description"].count("### HTTP 테스트 순서") == 1


@pytest.mark.parametrize(
    ("method", "example_key", "error_code", "field"),
    [
        ("post", "duplicate_name", "NETWORK_NAME_DUPLICATE", "body.name"),
        ("post", "duplicate_code", "NETWORK_CODE_DUPLICATE", "body.code"),
        ("post", "duplicate_auto", "DIMENSION_AUTO_CODE_DUPLICATE", "body.code"),
        ("patch", "duplicate_name", "NETWORK_NAME_DUPLICATE", "body.name"),
    ],
)
async def test_duplicate_error_examples_match_actual_response(
    client, method, example_key, error_code, field
):
    schema = (await client.get("/openapi.json")).json()
    created = await client.post("/networks", json={"name": "LTE"})
    assert created.status_code == 201
    template = "/networks" if method == "post" else "/networks/{network_id}"
    path = "/networks" if method == "post" else "/networks/" + created.json()["data"]["id"]
    if method == "patch":
        assert (await client.post("/networks", json={"name": "5G"})).status_code == 201
    request_example = body_examples(schema, template, method)[example_key]
    response = await client.request(method.upper(), path, json=request_example["value"])
    assert response.status_code == 409
    documented = schema["paths"][template][method]["responses"]["409"]["content"][
        "application/json"
    ]["examples"][error_code]["value"]["error"]
    actual = response.json()["error"]
    assert actual["code"] == error_code
    assert len(actual["details"]) == 1
    assert actual["details"][0]["field"] == field
    assert documented == actual


async def test_auto_code_example_reexecution_preserves_data_and_history(client):
    schema = (await client.get("/openapi.json")).json()
    example = body_examples(schema, "/networks", "post")["auto_code"]
    allowed_codes = {"NETWORK_NAME_DUPLICATE", "DIMENSION_AUTO_CODE_DUPLICATE"}
    for code in allowed_codes:
        assert code in example["description"]
    created = await client.post("/networks", json=example["value"])
    assert created.status_code == 201
    network = created.json()["data"]
    repeated = await client.post("/networks", json=example["value"])
    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] in allowed_codes
    assert (await client.get("/networks")).json()["data"] == [network]
    logs = (await client.get(f"/networks/{network['id']}/logs")).json()["data"]
    assert len(logs) == 1
    assert logs[0]["operation"] == "create"
    assert logs[0]["after"] == {key: network[key] for key in ("id", "name", "code")}
