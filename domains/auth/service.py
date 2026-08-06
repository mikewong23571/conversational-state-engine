"""Authentication service."""

from __future__ import annotations

import json
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from shared.database.connection import get_db

from .jwt_handler import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_jwt_token,
    verify_jwt_token,
)
from .models import Token, User, UserCreate

security = HTTPBearer()
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service layer for authentication operations."""

    def authenticate(self, email: str, password: str) -> User | None:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ? AND is_active = TRUE",
                (email,),
            ).fetchone()
            if not row:
                return None
            if not _pwd_context.verify(password, row["hashed_password"]):
                return None
            permissions = json.loads(row["permissions"])
            return User(
                user_id=row["user_id"],
                email=row["email"],
                role=row["role"],
                permissions=permissions,
            )

    def create_user(self, user_data: UserCreate) -> User:
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        hashed_password = _pwd_context.hash(user_data.password)
        permissions = {
            "admin": ["read", "write", "delete", "manage_users"],
            "editor": ["read", "write"],
            "user": ["read"],
        }.get(user_data.role, ["read"])
        with get_db() as conn:
            existing = conn.execute(
                "SELECT user_id FROM users WHERE email = ?", (user_data.email,)
            ).fetchone()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists",
                )
            conn.execute(
                """INSERT INTO users (user_id, email, hashed_password, role, permissions)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    user_id,
                    user_data.email,
                    hashed_password,
                    user_data.role,
                    json.dumps(permissions),
                ),
            )
            conn.commit()
        return User(
            user_id=user_id,
            email=user_data.email,
            role=user_data.role,
            permissions=permissions,
        )

    def create_token(self, user: User) -> Token:
        access_token = create_jwt_token({"sub": user.user_id})
        return Token(
            access_token=access_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    payload = verify_jwt_token(credentials.credentials)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ? AND is_active = TRUE",
            (user_id,),
        ).fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    permissions = json.loads(row["permissions"])
    return User(
        user_id=row["user_id"],
        email=row["email"],
        role=row["role"],
        permissions=permissions,
    )


def grant_session_access(
    session_id: str, user_id: str, permission_level: str = "read"
) -> None:
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO session_permissions
               (session_id, user_id, permission_level) VALUES (?, ?, ?)""",
            (session_id, user_id, permission_level),
        )
        conn.commit()


def check_session_access(session_id: str, user: User) -> bool:
    if user.role == "admin":
        return True
    with get_db() as conn:
        perm = conn.execute(
            """SELECT permission_level FROM session_permissions
               WHERE session_id = ? AND user_id = ?""",
            (session_id, user.user_id),
        ).fetchone()
    if not perm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this session",
        )
    return True


def init_auth_db() -> None:
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                permissions TEXT NOT NULL DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            );

            CREATE TABLE IF NOT EXISTS session_permissions (
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                permission_level TEXT NOT NULL DEFAULT 'read',
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                PRIMARY KEY (session_id, user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_session_permissions_user ON session_permissions(user_id);
            """
        )
        conn.commit()
        existing = conn.execute(
            "SELECT user_id FROM users WHERE email = ?",
            ("test@example.com",),
        ).fetchone()
        if not existing:
            hashed_password = _pwd_context.hash("test123")
            permissions = ["read", "write", "delete", "manage_users"]
            user_id = f"user_{uuid.uuid4().hex[:8]}"
            conn.execute(
                """INSERT INTO users (user_id, email, hashed_password, role, permissions)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    user_id,
                    "test@example.com",
                    hashed_password,
                    "admin",
                    json.dumps(permissions),
                ),
            )
            conn.commit()
