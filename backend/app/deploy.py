"""Container entry point with optional, explicitly configured schema bootstrap."""

import logging
import os

import uvicorn

from app.config import load_settings
from app.db.migrate import run_migrations
from app.db.seed import run_seed
from app.logging import LOG_CONFIG, configure_logging


def main() -> int:
    configure_logging()
    try:
        settings = load_settings()
        if settings.database_direct_url is not None:
            run_migrations(settings)
            run_seed(settings)
        uvicorn.run(
            "app.main:application", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")),
            workers=1, proxy_headers=True,
            forwarded_allow_ips=os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1"),
            log_config=LOG_CONFIG, access_log=False,
        )
    except Exception:
        logging.getLogger("lumalab").error("server_start_failed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
