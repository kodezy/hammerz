import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.errors import AppError, ErrorBody, ErrorCode
from app.db.session import get_session_factory
from app.db.tables import Auction
from app.modules.journal import Journal


def _build_journal() -> Journal:
    settings = get_settings()
    journal = Journal(
        settings.audit_dir,
        settings.hmac_secret.encode(),
        settings.deployment_id,
    )
    db_has = False
    try:
        with get_session_factory()() as session:
            has_auctions = session.scalar(select(func.count()).select_from(Auction)) or 0
            db_has = has_auctions > 0
    except Exception:
        db_has = False
    journal.open(db_has_auctions=db_has)
    return journal


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.journal = _build_journal()
    yield


def create_app() -> FastAPI:
    application = FastAPI(title="Hammerz", lifespan=lifespan)
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
