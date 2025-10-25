from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import init_db

settings = get_settings()


def create_application() -> FastAPI:
    application = FastAPI(title=settings.app_name)
    if settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=True,
        )
    application.include_router(api_router, prefix=settings.api_v1_prefix)
    return application


app = create_application()


@app.on_event("startup")
def on_startup() -> None:
    init_db()
