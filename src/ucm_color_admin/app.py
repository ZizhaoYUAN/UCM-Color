"""FastAPI application factory."""

from __future__ import annotations

from pathlib import Path
from typing import Generator

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from . import __version__, crud, schemas
from .config import get_settings
from .database import SessionLocal, init_database


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    init_database()

    app = FastAPI(title=settings.app_name, version=__version__)
    installer_root = settings.installer_dir.resolve()

    @app.get("/health", tags=["system"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/users", response_model=list[schemas.UserRead], tags=["users"])
    def list_users(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
        return crud.list_users(db, skip=skip, limit=limit)

    @app.post("/users", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED, tags=["users"])
    def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
        try:
            return crud.create_user(db, user)
        except crud.DuplicateUsernameError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @app.get("/users/{user_id}", response_model=schemas.UserRead, tags=["users"])
    def get_user(user_id: int, db: Session = Depends(get_db)):
        user = crud.get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    @app.put("/users/{user_id}", response_model=schemas.UserRead, tags=["users"])
    def update_user(user_id: int, payload: schemas.UserUpdate, db: Session = Depends(get_db)):
        user = crud.get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return crud.update_user(db, user, payload)

    @app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["users"])
    def delete_user(user_id: int, db: Session = Depends(get_db)) -> None:
        user = crud.get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        crud.delete_user(db, user)

    @app.get("/downloads", response_model=list[schemas.DownloadEntry], tags=["downloads"])
    def list_downloads(request: Request) -> list[schemas.DownloadEntry]:
        if not installer_root.exists():
            return []

        entries: list[schemas.DownloadEntry] = []
        for path in sorted(installer_root.glob("*")):
            if not path.is_file():
                continue
            entries.append(
                schemas.DownloadEntry(
                    filename=path.name,
                    url=str(request.url_for("download_installer", filename=path.name)),
                    size=path.stat().st_size,
                )
            )
        return entries

    @app.get(
        "/downloads/{filename}",
        name="download_installer",
        response_class=FileResponse,
        tags=["downloads"],
    )
    def download_installer(filename: str) -> FileResponse:
        safe_name = Path(filename).name
        requested = (installer_root / safe_name).resolve()
        try:
            requested.relative_to(installer_root)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Installer not found") from exc
        if not requested.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Installer not found")
        return FileResponse(requested)

    return app
