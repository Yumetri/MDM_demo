from uuid import UUID

import pytest
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.types import Receive, Scope, Send

from mdm_demo.app import create_app
from mdm_demo.composition.feature import FeatureModule


def feature(*routers: APIRouter) -> FeatureModule:
    return FeatureModule("extension", routers, lambda app, resources: None, ())


async def response():
    return {"ok": True}


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("/items/{id}", "/items/{name}"),
        ("/items/{id}", "/items/{name:str}"),
        ("/items/{id:int}", "/items/{name:int}"),
        ("/items/{id:uuid}", "/items/{name:uuid}"),
        ("/items/{rest:path}", "/items/{tail:path}"),
        ("/items", "/items"),
    ],
)
def test_rejects_equivalent_http_matchers(first, second):
    router = APIRouter()
    router.add_api_route(first, response, methods=["GET"])
    router.add_api_route(second, response, methods=["GET"])
    with pytest.raises(ValueError, match="Duplicate route"):
        create_app(modules=(feature(router),))


def test_nested_router_prefixes_participate_in_duplicate_detection():
    nested = APIRouter(prefix="/items")
    nested.add_api_route("/{id:int}", response)
    parent = APIRouter(prefix="/v1")
    parent.include_router(nested)
    other = APIRouter()
    other.add_api_route("/v1/items/{name:int}", response)
    with pytest.raises(ValueError, match="Duplicate route"):
        create_app(modules=(feature(parent, other),))


@pytest.mark.parametrize("path", ["/docs", "/openapi.json", "/health"])
@pytest.mark.parametrize("dynamic", [False, True])
def test_rejects_literal_and_dynamic_reserved_url_collisions(path, dynamic):
    router = APIRouter()
    # A broad route is rejected even when the built-in handler precedes it.
    router.add_api_route(path[:2] + "{rest:path}" if dynamic else path, response)
    with pytest.raises(ValueError, match="Duplicate route|Reserved route"):
        create_app(modules=(feature(router),))


def test_schema_hidden_starlette_route_also_participates():
    router = APIRouter()

    async def raw_response(request):
        return JSONResponse({"raw": True})

    router.add_route("/items/{id}", raw_response, methods=["GET"], include_in_schema=False)
    router.add_api_route("/items/{name}", response)
    parent = APIRouter()
    parent.include_router(router, prefix="/v1")
    with pytest.raises(ValueError, match="Duplicate route"):
        create_app(modules=(feature(parent),))


async def test_disjoint_converters_reach_both_handlers_with_same_parameter_name():
    router = APIRouter()

    async def numeric(id: int):
        return {"kind": "int", "id": id}

    async def uuid(id: UUID):
        return {"kind": "uuid", "id": str(id)}

    # OpenAPI has no converter syntax; this test concerns runtime dispatch only.
    router.add_api_route("/items/{id:int}", numeric, include_in_schema=False)
    router.add_api_route("/items/{id:uuid}", uuid, include_in_schema=False)
    app = create_app(modules=(feature(router),))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/items/42")).json() == {"kind": "int", "id": 42}
        value = "12345678-1234-5678-1234-567812345678"
        assert (await client.get(f"/items/{value}")).json() == {"kind": "uuid", "id": value}


async def test_distinct_methods_and_prefixes_are_allowed():
    router = APIRouter()
    router.add_api_route("/items/{id}", response, methods=["GET"])
    router.add_api_route("/items/{name}", response, methods=["POST"])
    router.add_api_route("/other/{name}", response, methods=["GET"])
    router.add_api_route("/docs", response, methods=["POST"])
    app = create_app(modules=(feature(router),))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for method, path in [
            ("GET", "/items/a"),
            ("POST", "/items/b"),
            ("GET", "/other/c"),
            ("POST", "/docs"),
        ]:
            assert (await client.request(method, path)).json() == {"ok": True}
        assert "text/html" in (await client.get("/docs")).headers["content-type"]
        assert "openapi" in (await client.get("/openapi.json")).json()
        assert (await client.get("/health")).status_code == 204


def test_overlapping_method_sets_are_rejected():
    router = APIRouter()
    router.add_api_route("/items/{id}", response, methods=["GET", "POST"])
    router.add_api_route("/items/{name}", response, methods=["POST", "PUT"])
    with pytest.raises(ValueError, match="Duplicate route: POST"):
        create_app(modules=(feature(router),))


def test_openapi_builtin_head_method_is_reserved():
    router = APIRouter()
    router.add_api_route("/{rest:path}", response, methods=["HEAD"])
    with pytest.raises(ValueError, match="Reserved route: HEAD"):
        create_app(modules=(feature(router),))


class RawEndpoint:
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await JSONResponse({"raw": True})(scope, receive, send)


async def raw_response(request):
    return JSONResponse({"raw": True})


def unrestricted_router(path: str, *, empty_methods: bool) -> APIRouter:
    router = APIRouter()
    # ASGI objects default to None; functions need an explicit empty list.
    router.routes.append(
        Route(
            path,
            raw_response if empty_methods else RawEndpoint(),
            methods=[] if empty_methods else None,
            include_in_schema=False,
        )
    )
    return router


@pytest.mark.parametrize("path", ["/docs", "/openapi.json", "/health"])
@pytest.mark.parametrize("dynamic", [False, True])
@pytest.mark.parametrize("empty_methods", [False, True])
def test_unrestricted_routes_cannot_consume_reserved_urls(path, dynamic, empty_methods):
    router = unrestricted_router(
        path[:2] + "{rest:path}" if dynamic else path, empty_methods=empty_methods
    )
    with pytest.raises(ValueError, match="Duplicate route|Reserved route"):
        create_app(modules=(feature(router),))


@pytest.mark.parametrize("method", ["GET", "PROPFIND", None])
@pytest.mark.parametrize("reverse", [False, True])
def test_unrestricted_matchers_conflict_in_both_registration_orders(method, reverse):
    wildcard = unrestricted_router("/items/{id}", empty_methods=False)
    other = APIRouter()
    other.routes.append(
        Route(
            "/items/{name}",
            RawEndpoint(),
            methods=[method] if method else None,
            include_in_schema=False,
        )
    )
    parent = APIRouter()
    for router in (other, wildcard) if reverse else (wildcard, other):
        parent.include_router(router, prefix="/v1")
    with pytest.raises(ValueError, match="Duplicate route"):
        create_app(modules=(feature(parent),))


@pytest.mark.parametrize("empty_methods", [False, True])
async def test_unrestricted_routes_with_distinct_prefix_remain_usable(empty_methods):
    wildcard = unrestricted_router("/extensions/{id}", empty_methods=empty_methods)
    other = APIRouter()
    other.add_api_route("/items/{name}", response)
    app = create_app(modules=(feature(wildcard, other),))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for method in ["GET", "POST", "PROPFIND"]:
            assert (await client.request(method, "/extensions/example")).json() == {"raw": True}
        assert (await client.get("/items/example")).json() == {"ok": True}
