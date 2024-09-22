"""
Some middleware to help with development work, or for extra debugging
"""

import json

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp

from fiber.logging_utils import get_logger

logger = get_logger(__name__)



async def _logging_middleware(request: Request, call_next) -> Response:
    logger.debug(f"Received request: {request.method} {request.url}")
    logger.debug(f"Request headers: {request.headers}")

    try:
        body = await request.body()
        logger.debug(f"Request body: {body.decode()}")
    except Exception as e:
        logger.error(f"Error reading request body: {e}")

    response = await call_next(request)
    logger.debug(f"Response status: {response.status_code}")

    if response.status_code != 200:
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        async def new_body_iterator():
            yield response_body

        response.body_iterator = new_body_iterator()
        logger.error(f"Response error content: {response_body.decode()}")

    return response


async def _custom_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"An error occurred: {exc}", exc_info=True)

    # Try to provide more specific error information
    if isinstance(exc, json.JSONDecodeError):
        return JSONResponse(content={"detail": "Invalid JSON in request body"}, status_code=400)
    elif isinstance(exc, ValueError):
        return JSONResponse(content={"detail": str(exc)}, status_code=400)

    return JSONResponse(content={"detail": "Internal Server Error"})


def configure_extra_logging_middleware(app: FastAPI):
    app.middleware("http")(_logging_middleware)
    app.add_exception_handler(Exception, _custom_exception_handler)
    logger.info("Development middleware and exception handler added.")
