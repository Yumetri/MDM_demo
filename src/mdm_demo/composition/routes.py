"""Reject duplicate HTTP matchers and collisions with app-owned endpoints."""

import re
from collections.abc import Collection, Sequence
from itertools import count

from fastapi.routing import iter_route_contexts
from starlette.routing import PARAM_REGEX, BaseRoute, Route, compile_path


def _matcher_key(path: str) -> str:
    positions = count()

    def parameter(match: re.Match[str]) -> str:
        return "{p" + str(next(positions)) + (match.group(2) or "") + "}"

    canonical_path = PARAM_REGEX.sub(parameter, path)
    return compile_path(canonical_path)[0].pattern


# Starlette treats both None and an empty method set as unrestricted.
type _Methods = set[str] | None


def _overlapping_methods(left: _Methods, right: _Methods) -> _Methods:
    if left is None:
        return right
    if right is None:
        return left
    return left & right


def validate_http_routes(routes: Sequence[BaseRoute], *, reserved_paths: Collection[str]) -> None:
    """Compare identical matchers, not arbitrary regex intersections.

    Parameter names do not affect matching; converter regexes do. Additionally,
    reject any HTTP matcher that consumes an app-owned concrete URL using the
    same method, regardless of registration order or schema visibility.
    """
    http_routes: list[tuple[str, _Methods]] = []
    for context in iter_route_contexts(routes):
        if not isinstance(context.original_route, Route):
            continue
        # Included plain Starlette routes store prefixed metadata on this wrapper.
        effective = getattr(context, "starlette_route", None) or context
        path = effective.path
        if path is not None:
            http_routes.append((path, effective.methods or None))
    reserved = [(path, methods) for path, methods in http_routes if path in reserved_paths]
    operations: dict[str, list[tuple[str, _Methods]]] = {}
    for path, methods in http_routes:
        matcher = _matcher_key(path)
        for previous_path, previous_methods in operations.get(matcher, []):
            overlap = _overlapping_methods(methods, previous_methods)
            if overlap is None or overlap:
                label = ",".join(sorted(overlap)) if overlap else "*"
                raise ValueError(f"Duplicate route: {label} {path} conflicts with {previous_path}")
        operations.setdefault(matcher, []).append((path, methods))
        pattern = compile_path(path)[0]
        for owned_path, owned_methods in reserved:
            if path == owned_path or not pattern.match(owned_path):
                continue
            overlap = _overlapping_methods(methods, owned_methods)
            if overlap is None or overlap:
                label = ",".join(sorted(overlap)) if overlap else "*"
                raise ValueError(f"Reserved route: {label} {path} conflicts with {owned_path}")
