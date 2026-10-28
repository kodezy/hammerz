import asyncio
import contextlib
import uuid
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from src.api.auctions import router as auctions_router
from src.api.auth import router as auth_router
from src.api.catalog import router as catalog_router
from src.api.health import router as health_router
from src.api.participations import router as participations_router
from src.api.receipts import router as receipts_router
from src.api.seller import router as seller_router
from src.api.wallet import router as wallet_router
from src.core.config import get_settings, parse_cors_origins
from src.core.errors import AppError, ErrorBody, ErrorCode
from src.core.limits import limiter
from src.db.session import get_session_factory
from src.db.tables import Auction
from src.modules.journal import Journal
from src.modules.settle import close_due_auctions
from src.realtime.hub import Hub

_WS_CAP = 20


def _build_journal() -> Journal:
    settings = get_settings()
    journal = Journal(settings.audit_dir, settings.hmac_secret.encode(), settings.deployment_id)
    db_has = False
    try:
        with get_session_factory()() as session:
            has_auctions = session.scalar(select(func.count()).select_from(Auction)) or 0
            db_has = has_auctions > 0
    except Exception:
        db_has = False
    journal.open(db_has_auctions=db_has)
    return journal


async def _settle_loop(application: FastAPI) -> None:
    settings = get_settings()
    while True:
        try:
            await close_due_auctions(application.state.journal, application.state.hub)
        except Exception:
            pass
        await asyncio.sleep(settings.settle_interval_seconds)


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.journal = _build_journal()
    application.state.hub = Hub()
    await close_due_auctions(application.state.journal, application.state.hub)
    settler = asyncio.create_task(_settle_loop(application))
    yield
    settler.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await settler


def create_app() -> FastAPI:
    application = FastAPI(title="Hammerz", lifespan=lifespan)
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(catalog_router)
    application.include_router(auctions_router)
    application.include_router(wallet_router)
    application.include_router(participations_router)
    application.include_router(receipts_router)
    application.include_router(seller_router)

    @application.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        return response

    @application.websocket("/ws/auctions/{auction_id}")
    async def auction_ws(websocket: WebSocket, auction_id: uuid.UUID):
        settings = get_settings()
        origin = websocket.headers.get("origin")
        allowed = {urlparse(o).netloc for o in parse_cors_origins(settings.cors_origins)}
        if origin:
            if urlparse(origin).netloc not in allowed:
                await websocket.accept()
                await websocket.send_json({"type": "ws.error", "code": "WS_ORIGIN"})
                await websocket.close()
                return
        client_host = websocket.client.host if websocket.client else "unknown"
        if not limiter.allow(f"ws:{client_host}", _WS_CAP):
            await websocket.accept()
            await websocket.send_json({"type": "ws.error", "code": "WS_LIMIT"})
            await websocket.close()
            return
        with get_session_factory()() as session:
            auction = session.get(Auction, auction_id)
            if auction is None:
                await websocket.accept()
                await websocket.send_json({"type": "ws.error", "code": "WS_NOT_FOUND"})
                await websocket.close()
                return
        hub: Hub = application.state.hub
        await hub.join(str(auction_id), websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await hub.leave(str(auction_id), websocket)

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
