import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.core.errors import AppError, ErrorBody, ErrorCode


def create_app() -> FastAPI:
    application = FastAPI(title="Hammerz")
    application.include_router(health_router)
    application.include_router(auth_router)

    @application.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        return response

    @application.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        body = ErrorBody(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=getattr(request.state, "request_id", None),
        )
        return JSONResponse(status_code=exc.status, content=body.model_dump(exclude_none=True))

    @application.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        body = ErrorBody(
            code=ErrorCode.VALIDATION_ERROR,
            message="Validation error",
            details={"errors": exc.errors()},
            request_id=getattr(request.state, "request_id", None),
        )
        return JSONResponse(status_code=422, content=body.model_dump(exclude_none=True))

    return application


app = create_app()
