"""Centralized error models and global exception handlers for FastAPI."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str


class ErrorPayload(BaseModel):
    code: str
    message: str
    status: int
    details: list[ErrorDetail] = []
    path: Optional[str] = None
    timestamp: Optional[str] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorPayload
    detail: Optional[str] = None
    path: Optional[str] = None
    timestamp: Optional[str] = None


STATUS_CODE_MAP = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    status.HTTP_409_CONFLICT: "CONFLICT",
    422: "VALIDATION_ERROR",
    status.HTTP_429_TOO_MANY_REQUESTS: "TOO_MANY_REQUESTS",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_SERVER_ERROR",
    status.HTTP_502_BAD_GATEWAY: "BAD_GATEWAY",
    status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
    status.HTTP_504_GATEWAY_TIMEOUT: "GATEWAY_TIMEOUT",
}


def build_error_response(
    status_code: int,
    code: str,
    message: str,
    details: Optional[list[ErrorDetail]] = None,
    headers: Optional[dict[str, str]] = None,
    request: Optional[Request] = None,
) -> JSONResponse:
    details_list = details or []
    now_iso = datetime.now(timezone.utc).isoformat()
    req_path = request.url.path if request else None

    content = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "status": status_code,
            "details": [d.model_dump() for d in details_list],
            "path": req_path,
            "timestamp": now_iso,
        },
        "detail": message,
        "path": req_path,
        "timestamp": now_iso,
    }
    resp_headers = headers.copy() if headers else {}
    if request:
        origin = request.headers.get("origin")
        if origin:
            resp_headers["Access-Control-Allow-Origin"] = origin
            resp_headers["Access-Control-Allow-Credentials"] = "true"
            resp_headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            resp_headers["Access-Control-Allow-Headers"] = "*"
        elif "Access-Control-Allow-Origin" not in resp_headers:
            resp_headers["Access-Control-Allow-Origin"] = "*"
    return JSONResponse(status_code=status_code, content=content, headers=resp_headers)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Standardize FastAPI / Pydantic validation errors (422)."""
    details: list[ErrorDetail] = []
    field_summaries: list[str] = []

    for err in exc.errors():
        loc = err.get("loc", ())
        loc_parts = [str(x) for x in loc if x != "body"]
        field_str = ".".join(loc_parts)
        msg = err.get("msg", "Invalid value")

        details.append(ErrorDetail(field=field_str or None, message=msg))
        if field_str:
            field_summaries.append(f"{field_str}: {msg}")
        else:
            field_summaries.append(msg)

    summary_message = "; ".join(field_summaries) if field_summaries else "Validation failed"

    return build_error_response(
        status_code=422,
        code="VALIDATION_ERROR",
        message=summary_message,
        details=details,
        request=request,
    )


async def http_exception_handler(
    request: Request, exc: HTTPException | StarletteHTTPException
) -> JSONResponse:
    """Standardize FastAPI and Starlette HTTPExceptions (400, 401, 403, 404, etc.)."""
    code = STATUS_CODE_MAP.get(exc.status_code, "ERROR")
    details: list[ErrorDetail] = []
    message = ""

    if isinstance(exc.detail, dict):
        message = str(exc.detail.get("message") or exc.detail.get("detail") or "Request failed")
        raw_errors = exc.detail.get("errors", [])
        if isinstance(raw_errors, list):
            for err in raw_errors:
                err_str = str(err)
                parts = err_str.split(":", 1)
                if len(parts) == 2:
                    details.append(ErrorDetail(field=parts[0].strip(), message=parts[1].strip()))
                else:
                    details.append(ErrorDetail(field=None, message=err_str))
    elif isinstance(exc.detail, list):
        items = [str(x) for x in exc.detail]
        message = "; ".join(items)
        details = [ErrorDetail(message=x) for x in items]
    else:
        if exc.status_code == 404 and exc.detail == "Not Found":
            message = "Resource or endpoint not found"
        else:
            message = str(exc.detail) if exc.detail else "Request failed"

    headers = getattr(exc, "headers", None)
    return build_error_response(
        status_code=exc.status_code,
        code=code,
        message=message,
        details=details,
        headers=headers,
        request=request,
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all for unhandled server exceptions (500)."""
    logger.exception("Unhandled server exception: %s %s", request.method, request.url)
    return build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred. Please try again.",
        request=request,
    )
