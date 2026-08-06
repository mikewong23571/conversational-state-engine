"""Authentication REST endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from domains.auth import (
    AuthService,
    Token,
    User,
    UserCreate,
    UserLogin,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service() -> AuthService:
    return AuthService()


@router.post("/register", response_model=dict)
async def register(
    user_data: UserCreate, service: AuthService = Depends(get_auth_service)
) -> dict[str, str]:
    user = service.create_user(user_data)
    return {"message": "User created successfully", "user_id": user.user_id}


@router.post("/login", response_model=Token)
async def login(
    user: UserLogin, service: AuthService = Depends(get_auth_service)
) -> Token:
    auth_user = service.authenticate(user.email, user.password)
    if not auth_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    return service.create_token(auth_user)


@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
