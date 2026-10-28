from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from src.api.deps import client_ip, get_current_user
from src.core.errors import AppError, ErrorBody, ErrorCode
from src.core.limits import limiter
from src.core.security import REFRESH_TTL
from src.db.session import get_db
from src.db.tables import User
from src.modules import auth as auth_module

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

REFRESH_COOKIE = "hammerz_refresh"
REFRESH_MAX_AGE = int(REFRESH_TTL.total_seconds())


def _email(value: str) -> str:
    try:
        parsed = validate_email(value.strip(), check_deliverability=False, test_environment=True)
    except EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc
    return parsed.normalized


Email = Annotated[str, AfterValidator(_email)]


class RegisterBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: Email
    password: str = Field(min_length=8, max_length=128)


class LoginBody(BaseModel):
    email: Email
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    role: str


class TokenOut(BaseModel):
    token: str
    token_type: str = "bearer"


def _cookie_secure(request: Request) -> bool:
    if request.url.scheme == "https":
        return True
    forwarded = request.headers.get("x-forwarded-proto", "")
    return forwarded.split(",")[0].strip().lower() == "https"


def _set_refresh_cookie(response: Response, request: Request, raw: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=raw,
        max_age=REFRESH_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(request),
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response, request: Request) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE, path="/api/v1/auth", secure=_cookie_secure(request), httponly=True, samesite="lax"
    )


def _token_response(request: Request, access: str, refresh_raw: str | None) -> JSONResponse:
    body = TokenOut(token=access)
    response = JSONResponse(content=body.model_dump())
    if refresh_raw is not None:
        _set_refresh_cookie(response, request, refresh_raw)
    return response


@router.post("/register", status_code=201, response_model=UserOut)
async def register(body: RegisterBody, request: Request, session: Session = Depends(get_db)) -> UserOut:
    ip = client_ip(request)
    if not limiter.allow(f"register:{ip}", 5):
        raise AppError(429, ErrorCode.RATE_LIMITED, "Too many registration attempts")
    user = await auth_module.register(session, body.email, body.password)
    return UserOut(id=str(user.id), email=user.email, role=user.role)


@router.post("/login")
async def login(body: LoginBody, request: Request, session: Session = Depends(get_db)) -> JSONResponse:
    ip = client_ip(request)
    if not limiter.allow(f"login:{ip}", 10):
        raise AppError(429, ErrorCode.RATE_LIMITED, "Too many login attempts")
    access, refresh_raw = await auth_module.login(session, body.email, body.password)
    return _token_response(request, access, refresh_raw)


@router.post("/refresh")
async def refresh(request: Request, session: Session = Depends(get_db)) -> JSONResponse:
    ip = client_ip(request)
    if not limiter.allow(f"refresh:{ip}", 30):
        raise AppError(429, ErrorCode.RATE_LIMITED, "Too many refresh attempts")
    refresh_raw = request.cookies.get(REFRESH_COOKIE)
    if not refresh_raw:
        raise AppError(401, ErrorCode.UNAUTHORIZED, "Authentication required")
    try:
        access = auth_module.refresh_session(session, refresh_raw)
    except AppError as exc:
        if exc.status == 401:
            body = ErrorBody(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=getattr(request.state, "request_id", None),
            )
            response = JSONResponse(status_code=401, content=body.model_dump(exclude_none=True))
            _clear_refresh_cookie(response, request)
            return response
        raise
    return _token_response(request, access, None)


@router.post("/logout", status_code=204)
async def logout(request: Request, session: Session = Depends(get_db)) -> Response:
    refresh_raw = request.cookies.get(REFRESH_COOKIE)
    if refresh_raw:
        auth_module.revoke_refresh(session, refresh_raw)
    response = Response(status_code=204)
    _clear_refresh_cookie(response, request)
    return response


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=str(user.id), email=user.email, role=user.role)
