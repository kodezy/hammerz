from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, Request
from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from src.api.deps import client_ip, get_current_user
from src.core.errors import AppError, ErrorCode
from src.core.limits import limiter
from src.db.session import get_db
from src.db.tables import User
from src.modules import auth as auth_module

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


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


@router.post("/register", status_code=201, response_model=UserOut)
async def register(body: RegisterBody, request: Request, session: Session = Depends(get_db)) -> UserOut:
    ip = client_ip(request)
    if not limiter.allow(f"register:{ip}", 5):
        raise AppError(429, ErrorCode.RATE_LIMITED, "Too many registration attempts")
    user = await auth_module.register(session, body.email, body.password)
    return UserOut(id=str(user.id), email=user.email, role=user.role)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginBody, request: Request, session: Session = Depends(get_db)) -> TokenOut:
    ip = client_ip(request)
    if not limiter.allow(f"login:{ip}", 10):
        raise AppError(429, ErrorCode.RATE_LIMITED, "Too many login attempts")
    token = await auth_module.login(session, body.email, body.password)
    return TokenOut(token=token)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=str(user.id), email=user.email, role=user.role)
