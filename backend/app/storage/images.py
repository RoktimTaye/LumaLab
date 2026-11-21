"""Private, process-local sessions; serialize access with processing and deletion."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import secrets
import shutil
from threading import BoundedSemaphore, Condition, RLock

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
    width: int
    height: int
    readers: int = 0
    retiring: bool = False


class ImageStore:
    def __init__(self, directory: Path, settings: Settings):
        self.directory, self.settings = directory, settings
        self.sessions: dict[str, Session] = {}
        self.lock = RLock()
        self.idle = Condition(self.lock)
        self.processing = BoundedSemaphore(1)
        self.previews = BoundedSemaphore(2)
        self.stored_bytes = 0

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
            for name, edge in (("preview.png", self.settings.preview_max_edge), ("analysis.png", 512)):
                with image.copy() as reduced:
                    reduced.thumbnail((edge, edge), Image.Resampling.LANCZOS if name == "preview.png" else Image.Resampling.BICUBIC)
                    reduced.save(directory / name, format="PNG")
            stored_bytes = sum(path.stat().st_size for path in directory.iterdir() if path.is_file())

        except Exception:
            shutil.rmtree(directory)
            raise
        with self.lock:
            if len(self.sessions) >= 32 or self.stored_bytes + stored_bytes > self.settings.max_temp_image_bytes:
                shutil.rmtree(directory)
                raise ImageError(429, "storage_capacity_exceeded", "Temporary image storage is full. Delete an image and try again.")
            self.stored_bytes += stored_bytes
            uploaded_at = datetime.now(timezone.utc)
            expires = uploaded_at + timedelta(seconds=self.settings.image_ttl_seconds)
            self.sessions[image_id] = Session(directory, sha256(token.encode()).digest(), uploaded_at, expires, filename, image.width, image.height)
            return UploadedImage(image_id=image_id, access_token=token, filename=filename,
                                 format=detected, width=image.width, height=image.height, expires_at=expires)

    def purge_expired(self) -> None:
        with self.lock:
            now = datetime.now(timezone.utc)
            for image_id, session in list(self.sessions.items()):
                if session.expires_at <= now:
                    self._remove(image_id, session)

    def _remove(self, image_id: str, session: Session) -> None:
        # Called with the condition lock held. Waiting releases it so other
        # sessions and active readers can continue while deletion waits.
        session.retiring = True
        self.idle.wait_for(lambda: session.readers == 0)
        if self.sessions.get(image_id) is not session:
            return
        size = self._session_size(session.directory)
        if session.directory.exists():
            shutil.rmtree(session.directory)
        self.stored_bytes -= size
        del self.sessions[image_id]

    @staticmethod
    def _session_size(directory: Path) -> int:
        return sum(path.stat().st_size for path in directory.iterdir() if path.is_file()) if directory.exists() else 0

    @contextmanager
    def authorized(self, image_id: str, token: str) -> Iterator[Session]:
        with self.lock:
            session = self.sessions.get(image_id)
            if session is None or session.retiring:
                raise ImageError(404, "image_unavailable", "Image session is unavailable.")
            if not secrets.compare_digest(session.token_hash, sha256(token.encode()).digest()):
                raise ImageError(401, "unauthorized", "A valid image access token is required.")
            if session.expires_at <= datetime.now(timezone.utc):
                self._remove(image_id, session)
                raise ImageError(410, "image_expired", "Image session has expired.")
            session.readers += 1
        try:
            yield session
        finally:
            with self.idle:
                session.readers -= 1
                self.idle.notify_all()

    def delete(self, image_id: str, token: str) -> None:
        with self.authorized(image_id, token) as session:
            # Retire before releasing this reader to exclude new work.
            with self.lock:
                session.retiring = True
        with self.lock:
            self._remove(image_id, session)
