"""
Authentication and authorization module for Conversational State Engine
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# JWT Configuration
SECRET_KEY = (
    "your-secret-key-change-in-production"  # TODO: Move to environment variable
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token scheme
security = HTTPBearer()


# Models
class User(BaseModel):
    user_id: str
    email: str
    role: str
    permissions: list[str]


class UserLogin(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "user"


class Token(BaseModel):
    access_token: str
    token_type: str


# Database connection for auth
@contextmanager
def get_auth_db():
    conn = sqlite3.connect("state_engine.db")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# Initialize auth tables
def init_auth_db():
    """Initialize authentication database tables"""
    with get_auth_db() as conn:
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


# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# JWT utilities
def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# User management
def authenticate_user(email: str, password: str) -> Optional[User]:
    with get_auth_db() as conn:
        user_row = conn.execute(
            "SELECT * FROM users WHERE email = ? AND is_active = TRUE", (email,)
        ).fetchone()

        if not user_row:
            return None

        if not verify_password(password, user_row["hashed_password"]):
            return None

        import json

        permissions = json.loads(user_row["permissions"])

        return User(
            user_id=user_row["user_id"],
            email=user_row["email"],
            role=user_row["role"],
            permissions=permissions,
        )


def create_user(user_data: UserCreate) -> User:
    import json
    import uuid

    user_id = f"user_{uuid.uuid4().hex[:8]}"
    hashed_password = get_password_hash(user_data.password)

    # Default permissions based on role
    permissions = {
        "admin": ["read", "write", "delete", "manage_users"],
        "editor": ["read", "write"],
        "user": ["read"],
    }.get(user_data.role, ["read"])

    with get_auth_db() as conn:
        # Check if user already exists
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


def get_user_by_id(user_id: str) -> Optional[User]:
    with get_auth_db() as conn:
        user_row = conn.execute(
            "SELECT * FROM users WHERE user_id = ? AND is_active = TRUE", (user_id,)
        ).fetchone()

        if not user_row:
            return None

        import json

        permissions = json.loads(user_row["permissions"])

        return User(
            user_id=user_row["user_id"],
            email=user_row["email"],
            role=user_row["role"],
            permissions=permissions,
        )


# Dependency functions
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    payload = verify_token(token)

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_permission(permission: str):
    """Dependency factory for permission checking"""

    async def check_permission(user: User = Depends(get_current_user)) -> User:
        if permission not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission}",
            )
        return user

    return check_permission


def check_session_access(session_id: str, user: User) -> bool:
    """Check if user has access to specific session"""
    # Admins can access all sessions
    if user.role == "admin":
        return True

    with get_auth_db() as conn:
        permission = conn.execute(
            """SELECT permission_level FROM session_permissions
               WHERE session_id = ? AND user_id = ?""",
            (session_id, user.user_id),
        ).fetchone()

        # If no explicit permission, deny access
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this session",
            )

        return True


def grant_session_access(session_id: str, user_id: str, permission_level: str = "read"):
    """Grant user access to a session"""
    with get_auth_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO session_permissions
               (session_id, user_id, permission_level) VALUES (?, ?, ?)""",
            (session_id, user_id, permission_level),
        )
        conn.commit()
