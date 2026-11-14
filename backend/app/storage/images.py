"""Private, process-local sessions; serialize access with processing and deletion."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import secrets
import shutil
from threading import BoundedSemaphore, RLock

from PIL import Image

from app.config import Settings
from app.schemas.images import UploadedImage
from app.services.images import ImageError


@dataclass
class Session:
    directory: Path
    token_hash: bytes
    uploaded_at: datetime
    expires_at: datetime
    filename: str


class ImageStore:
    def __init__(self, directory: Path, settings: Settings):
        self.directory, self.settings = directory, settings
        self.sessions: dict[str, Session] = {}
        self.lock = RLock()
        self.processing = BoundedSemaphore(1)

    def create(self, data: bytes, image: Image.Image, filename: str, detected: str) -> UploadedImage:
        with self.lock:
            self.purge_expired()
            if len(self.sessions) >= 32:
                raise ImageError(429, "capacity_exceeded", "Image session capacity reached. Close an existing session.")
            image_id, token = secrets.token_hex(16), secrets.token_urlsafe(32)
            directory = self.directory / image_id
            directory.mkdir(mode=0o700)
            try:
                (directory / "original").write_bytes(data)
                image.save(directory / "normalized.png", format="PNG")
            except Exception:
                shutil.rmtree(directory)
                raise
            uploaded_at = datetime.now(timezone.utc)
            expires = uploaded_at + timedelta(seconds=self.settings.image_ttl_seconds)
            self.sessions[image_id] = Session(directory, sha256(token.encode()).digest(), uploaded_at, expires, filename)
            return UploadedImage(image_id=image_id, access_token=token, filename=filename,
                                 format=detected, width=image.width, height=image.height, expires_at=expires)

    def purge_expired(self) -> None:
        with self.lock:
            now = datetime.now(timezone.utc)
            for image_id, session in list(self.sessions.items()):
                if session.expires_at <= now:
                    if session.directory.exists():
                        shutil.rmtree(session.directory)
                    del self.sessions[image_id]

    @contextmanager
    def authorized(self, image_id: str, token: str) -> Iterator[Session]:
        with self.lock:
            session = self.sessions.get(image_id)
            if session is None:
                raise ImageError(404, "image_unavailable", "Image session is unavailable.")
            if not secrets.compare_digest(session.token_hash, sha256(token.encode()).digest()):
                raise ImageError(401, "unauthorized", "A valid image access token is required.")
            if session.expires_at <= datetime.now(timezone.utc):
                if session.directory.exists():
                    shutil.rmtree(session.directory)
                raise ImageError(410, "image_expired", "Image session has expired.")
            yield session

    def delete(self, image_id: str, token: str) -> None:
        with self.authorized(image_id, token) as session:
            shutil.rmtree(session.directory)
            del self.sessions[image_id]
