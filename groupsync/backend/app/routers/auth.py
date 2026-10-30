from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.config import settings
from app.deps import CurrentUser, DbSession
from app.models import Role, User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    PushTokenRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)
from app.security import create_token, decode_token, hash_password, verify_password
from app.services.rate_limit import FailureLimiter

router = APIRouter(prefix="/auth", tags=["auth"])

login_limiter = FailureLimiter(settings.login_max_attempts, settings.login_window_seconds)


def _tokens(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_token(user.id, "access"),
        refresh_token=create_token(user.id, "refresh"),
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: DbSession):
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already registered")
    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        role=Role(body.role),
    )
    db.add(user)
    db.commit()
    return AuthResponse(**_tokens(user).model_dump(), user=UserOut.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, request: Request, db: DbSession):
    # Key on IP + email so one attacker can't lock out an account from everywhere
    ip = request.client.host if request.client else "unknown"
    key = f"{ip}:{body.email}"
    wait = login_limiter.retry_after(key)
    if wait:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many failed login attempts. Try again later.",
            headers={"Retry-After": str(wait)},
        )
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None or not verify_password(body.password, user.password_hash):
        login_limiter.record_failure(key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    login_limiter.reset(key)
    return AuthResponse(**_tokens(user).model_dump(), user=UserOut.model_validate(user))


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: DbSession):
    user_id = decode_token(body.refresh_token, "refresh")
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")
    return _tokens(user)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.put("/push-token", response_model=UserOut)
def set_push_token(body: PushTokenRequest, user: CurrentUser, db: DbSession):
    user.push_token = body.push_token
    db.commit()
    return user
