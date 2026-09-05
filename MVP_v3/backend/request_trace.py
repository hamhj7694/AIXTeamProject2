"""Request correlation without logging request bodies, credentials or exception text."""
from contextlib import contextmanager
from contextvars import ContextVar
import logging
import re
from time import monotonic
from uuid import uuid4

request_id = ContextVar("request_id", default="background")
logger = logging.getLogger("uvicorn.error")


@contextmanager
def trace_stage(name):
    started = monotonic()
    logger.info("request_id=%s stage=%s state=start", request_id.get(), name)
    try:
        yield
    except BaseException as exc:
        logger.error("request_id=%s stage=%s state=failed error_type=%s cause_type=%s",
                     request_id.get(), name, type(exc).__name__, type(exc.__cause__).__name__)
        raise
    else:
        logger.info("request_id=%s stage=%s state=done elapsed_ms=%d",
                    request_id.get(), name, (monotonic() - started) * 1000)


def install_request_trace(app, service):
    @app.middleware("http")
    async def correlate(request, call_next):
        supplied = request.headers.get("X-Request-ID", "")
        correlation = supplied if re.fullmatch(r"[A-Za-z0-9_-]{1,80}", supplied) else uuid4().hex
        token = request_id.set(correlation)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = correlation
            # Only route templates: no query strings or customer identifiers.
            route = request.scope.get("route")
            logger.info("request_id=%s service=%s method=%s route=%s status=%d",
                        correlation, service, request.method, getattr(route, "path", "unmatched"), response.status_code)
            return response
        finally:
            request_id.reset(token)
