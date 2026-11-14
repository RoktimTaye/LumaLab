"""Export the actual API schema with synthetic settings; never open resources."""

import json
import os
from unittest.mock import patch

from app.config import Settings


def schema() -> dict:
    environment = {key: value for key, value in os.environ.items()
                   if key.upper() in {"SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "PATH", "TEMP", "TMP"}}
    environment["DATABASE_URL"] = "postgresql://schema:synthetic@db.invalid/schema?sslmode=require"
    with patch.dict(os.environ, environment, clear=True), patch.dict(Settings.model_config, {"env_file": None}):
        from app.main import app

        return app.openapi()


if __name__ == "__main__":
    print(json.dumps(schema(), sort_keys=True))
