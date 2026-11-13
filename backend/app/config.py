"""Validated backend settings; loading does not open connections or create files."""

from pathlib import Path
from urllib.parse import urlsplit

from psycopg import ProgrammingError
from psycopg.conninfo import conninfo_to_dict
from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, SettingsError

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
RUNTIME_DIR = BACKEND_DIR / ".runtime"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
    )

    database_url: SecretStr
    database_direct_url: SecretStr | None = None
    database_pool_max_size: int = Field(default=4, ge=1, le=20)
    database_timeout_seconds: int = Field(default=5, ge=1, le=60)
    temp_image_dir: Path = RUNTIME_DIR / "images"
    max_upload_bytes: int = Field(default=10_000_000, gt=0)
    max_image_pixels: int = Field(default=24_000_000, gt=0)
    max_image_side: int = Field(default=10_000, gt=0)
    preview_max_edge: int = Field(default=1_600, gt=0)
    image_ttl_seconds: int = Field(default=3_600, gt=0)
    cleanup_interval_seconds: int = Field(default=300, gt=0, le=300)
    jpeg_quality: int = Field(default=92, ge=1, le=100)
    allowed_origins: tuple[str, ...] = ()

    @field_validator("database_url", "database_direct_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        raw = value.get_secret_value()
        message = "must be a PostgreSQL URL with host, database, user, password and sslmode=require, verify-ca or verify-full"
        if not raw.startswith(("postgresql://", "postgres://")):
            raise ValueError(message)
        try:
            parameters = conninfo_to_dict(raw)
        except ProgrammingError:
            raise ValueError(message) from None
        if not all(parameters.get(key) for key in ("host", "dbname", "user", "password")):
            raise ValueError(message)
        if parameters.get("sslmode") not in {"require", "verify-ca", "verify-full"}:
            raise ValueError(message)
        return value

    @field_validator("temp_image_dir")
    @classmethod
    def validate_temp_image_dir(cls, value: Path) -> Path:
        path = (BACKEND_DIR / value).resolve()
        if path == PROJECT_DIR or path in PROJECT_DIR.parents:
            raise ValueError("must be a dedicated private directory")
        if path.is_relative_to(PROJECT_DIR) and not path.is_relative_to(RUNTIME_DIR):
            raise ValueError("inside the repository, use backend/.runtime for private image storage")
        return path

    @field_validator("allowed_origins")
    @classmethod
    def validate_allowed_origins(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        origins = []
        for value in values:
            try:
                parsed = urlsplit(value)
                valid = (
                    parsed.scheme in {"http", "https"}
                    and parsed.hostname
                    and "*" not in parsed.netloc
                    and parsed.username is None
                    and parsed.password is None
                    and parsed.path in {"", "/"}
                    and not parsed.query
                    and not parsed.fragment
                    and (parsed.port is None or parsed.port > 0)
                    and not any(character.isspace() for character in value)
                )
            except ValueError:
                valid = False
            if not valid:
                raise ValueError("must contain only explicit HTTP(S) origins without credentials, paths, queries or wildcards")
            origins.append(f"{parsed.scheme}://{parsed.netloc}")
        return tuple(origins)

    @model_validator(mode="after")
    def validate_related_limits(self) -> "Settings":
        if self.preview_max_edge > self.max_image_side:
            raise ValueError("PREVIEW_MAX_EDGE must not exceed MAX_IMAGE_SIDE")
        if self.cleanup_interval_seconds > self.image_ttl_seconds:
            raise ValueError("CLEANUP_INTERVAL_SECONDS must not exceed IMAGE_TTL_SECONDS")
        return self


def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as error:
        details = []
        for issue in error.errors(include_input=False, include_context=False, include_url=False):
            field = issue["loc"][0] if issue["loc"] else None
            name = str(field).upper() if field in Settings.model_fields else "settings"
            details.append(f"{name}: {issue['msg']}")
        raise RuntimeError("Invalid backend configuration: " + "; ".join(details)) from None
    except (SettingsError, OSError, UnicodeError):
        raise RuntimeError("Unable to load backend configuration; check environment variables and backend/.env syntax.") from None
