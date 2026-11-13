"""Console logs contain approved event names, never raw messages or exceptions."""

from datetime import datetime, timezone
import json
import logging
from logging.config import dictConfig

EVENTS = frozenset({
    "configuration_invalid", "server_start_failed", "startup_started", "startup_complete",
    "startup_failed", "shutdown_started", "shutdown_complete", "lifecycle_failed",
    "lifecycle_cancelled", "readiness_database_unavailable", "readiness_storage_unavailable",
    "database_pool_start_failed", "database_pool_close_failed",
    "storage_start_failed", "storage_cleanup_failed",
})


class SafeFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if record.name == "lumalab" and isinstance(record.msg, str) and record.msg in EVENTS:
            event = record.msg
        elif record.name == "psycopg" or record.name.startswith("psycopg."):
            event = "database_driver_event"
        elif record.name == "uvicorn" or record.name.startswith("uvicorn."):
            event = "server_event"
        else:
            event = "runtime_event"
        return json.dumps({
            "time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": logging.getLevelName(record.levelno),
            "event": event,
        })


LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"safe": {"()": "app.logging.SafeFormatter"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "safe", "stream": "ext://sys.stderr"}},
    "root": {"level": "WARNING", "handlers": ["console"]},
    "loggers": {
        "lumalab": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "uvicorn": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        "uvicorn.error": {"level": "WARNING", "handlers": [], "propagate": True},
        "uvicorn.access": {"handlers": [], "propagate": False},
        "psycopg": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        "psycopg.pool": {"level": "WARNING", "handlers": [], "propagate": True},
    },
}


def configure_logging() -> None:
    dictConfig(LOG_CONFIG)
    logging.getLogger("uvicorn.access").disabled = True
