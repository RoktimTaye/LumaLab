import argparse
import logging

import uvicorn

from app.logging import LOG_CONFIG, configure_logging

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the LumaLab backend.")
    parser.add_argument("--reload", action="store_true", help="Reload when backend code changes.")
    arguments = parser.parse_args()
    configure_logging()
    try:
        uvicorn.run(
            "app.main:app", host="127.0.0.1", port=8000, workers=1,
            reload=arguments.reload, log_config=LOG_CONFIG, log_level="warning", access_log=False,
        )
    except Exception:
        logging.getLogger("lumalab").error("server_start_failed")
        raise SystemExit(1) from None
