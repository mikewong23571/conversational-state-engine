from fastapi import FastAPI

from domains.auth import init_auth_db
from shared.database import init_db

from .middleware import setup_middleware
from .rest import auth, intentions, patches, sessions


def create_app() -> FastAPI:
    app = FastAPI(title="Conversational State Engine", version="0.1.0")
    setup_middleware(app)
    init_db()
    init_auth_db()
    app.include_router(auth.router)
    app.include_router(sessions.router)
    app.include_router(intentions.router)
    app.include_router(patches.router)

    @app.get("/")
    async def root():
        return {"name": "Conversational State Engine", "version": "0.1.0", "docs": "/docs"}

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app
