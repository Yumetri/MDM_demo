"""Preserve literal nulls inside executable examples after OpenAPI serialization."""

from copy import deepcopy
from typing import Any

from fastapi import FastAPI
from fastapi.params import Body
from fastapi.routing import APIRoute, iter_route_contexts


def register_openapi_examples(app: FastAPI) -> None:
    default_openapi = app.openapi

    def openapi() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = default_openapi()
        # FastAPI serializes the OpenAPI model with exclude_none=True, including
        # arbitrary example payloads. Restore only examples, not optional schema fields.
        for route in iter_route_contexts(app.routes):
            if not isinstance(route.original_route, APIRoute) or not route.include_in_schema:
                continue
            for method in route.methods or ():
                operation = schema["paths"][route.path_format][method.lower()]
                for field in route.dependant.body_params:
                    if not isinstance(field.field_info, Body):
                        continue
                    examples = field.field_info.openapi_examples
                    if examples:
                        media_type = field.field_info.media_type
                        operation["requestBody"]["content"][media_type]["examples"] = deepcopy(
                            examples
                        )
                for status, response in route.responses.items():
                    for media_type, content in response.get("content", {}).items():
                        if "examples" in content:
                            operation["responses"][str(status)]["content"][media_type][
                                "examples"
                            ] = deepcopy(content["examples"])
        return schema

    app.openapi = openapi
