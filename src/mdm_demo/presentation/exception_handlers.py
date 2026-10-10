import logging
from collections.abc import Mapping
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from mdm_demo.application.errors import ApplicationError
from mdm_demo.presentation.error_catalog import DETAIL_MESSAGES, ERRORS, HTTP_CODES
from mdm_demo.presentation.schemas.common import ErrorBody, ErrorDetail, ErrorResponse, Meta

logger = logging.getLogger(__name__)


def error_response(
    request: Request,
    code: str,
    details: list[ErrorDetail] | None = None,
    headers: Mapping[str, str] | None = None,
    status: int | None = None,
) -> JSONResponse:
    spec = ERRORS[code]
    request_id: UUID = request.state.request_id
    body = ErrorResponse(
        error=ErrorBody(code=code, message=spec.message, details=details or []),
        meta=Meta(request_id=request_id),
    )
    return JSONResponse(
        status_code=status or spec.status,
        content=body.model_dump(mode="json"),
        headers={**(headers or {}), "X-Request-ID": str(request_id)},
    )


async def application_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApplicationError)
    details = []
    if exc.field is not None:
        details.append(
            ErrorDetail(field=exc.field, code=exc.code, message=ERRORS[exc.code].message)
        )
    return error_response(request, exc.code, details)


async def validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = []
    for error in exc.errors():
        location = error.get("loc", ())
        field = ".".join(str(item) for item in location) or None
        code = (
            "OUT_OF_RANGE"
            if field == "query.limit" and error["type"] in {"greater_than_equal", "less_than_equal"}
            else "INVALID_VALUE"
        )
        # Never echo input, exception contexts, or framework messages.
        details.append(ErrorDetail(field=field, code=code, message=DETAIL_MESSAGES[code]))
    return error_response(request, "VALIDATION_ERROR", details)


async def http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    code = HTTP_CODES.get(exc.status_code, "INTERNAL_ERROR")
    return error_response(request, code, headers=exc.headers, status=exc.status_code)


async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "request_id=%s error=INTERNAL_ERROR exception_type=%s",
        request.state.request_id,
        type(exc).__name__,
    )
    return error_response(request, "INTERNAL_ERROR")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationError, application_error)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(Exception, unexpected_error)
