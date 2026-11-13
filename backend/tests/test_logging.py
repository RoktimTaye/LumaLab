"""Operational log privacy and launch configuration checks."""

import json
import logging
import subprocess
import sys
import unittest

from app.config import BACKEND_DIR
from app.logging import SafeFormatter

PRIVATE = "Bearer secret-token postgresql://user:password@private-host/db C:/private/photo.jpg GPS=private"


class LoggingTests(unittest.TestCase):
    def run_script(self, code):
        result = subprocess.run([sys.executable, "-c", code], cwd=BACKEND_DIR,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        return [json.loads(line) for line in result.stderr.splitlines()]

    def test_formatter_drops_arguments_exceptions_stack_and_extra_fields(self):
        try:
            raise RuntimeError(PRIVATE)
        except RuntimeError:
            record = logging.LogRecord("lumalab", logging.ERROR, PRIVATE, 1,
                                       "startup_failed", (PRIVATE,), sys.exc_info(), sinfo=PRIVATE)
        record.request_headers = PRIVATE
        record.photo_contents = PRIVATE
        record.exc_text = PRIVATE
        output = SafeFormatter().format(record)
        parsed = json.loads(output)
        self.assertEqual(set(parsed), {"time", "level", "event"})
        self.assertEqual(parsed["event"], "startup_failed")
        self.assertEqual(parsed["level"], "ERROR")
        self.assertTrue(parsed["time"].endswith("+00:00"))
        self.assertNotIn(PRIVATE, output)
        self.assertNotIn("Traceback", output)

    def test_unknown_and_third_party_messages_use_fixed_categories(self):
        for name, expected in (("lumalab", "runtime_event"), ("psycopg.pool", "database_driver_event"),
                               ("uvicorn.error", "server_event"), (PRIVATE, "runtime_event")):
            with self.subTest(logger=name):
                record = logging.LogRecord(name, logging.WARNING, PRIVATE, 1, PRIVATE, (), None)
                self.assertEqual(json.loads(SafeFormatter().format(record))["event"], expected)

    def test_configuration_is_repeatable_and_access_logs_are_disabled(self):
        records = self.run_script("""
import logging
from app.logging import configure_logging
configure_logging()
configure_logging()
logging.getLogger('lumalab').info('startup_complete')
logging.getLogger('uvicorn.access').error('Bearer secret-token /private/photo.jpg')
logging.getLogger('uvicorn.error').error('postgresql://user:password@host/db')
logging.getLogger('psycopg.pool').warning('private-host C:/private/photo.jpg')
""")
        self.assertEqual([record["event"] for record in records],
                         ["startup_complete", "server_event", "database_driver_event"])

    def test_reload_entry_point_retains_safe_logging_configuration(self):
        records = self.run_script("""
import logging
import runpy
import sys
from unittest.mock import patch
from app.logging import LOG_CONFIG
sys.argv = ['app', '--reload']
with patch('uvicorn.run') as run:
    runpy.run_module('app', run_name='__main__')
    assert run.call_args.kwargs['reload'] is True
    assert run.call_args.kwargs['access_log'] is False
    assert run.call_args.kwargs['log_config'] == LOG_CONFIG
    assert run.call_args.kwargs['workers'] == 1
logging.getLogger('lumalab').info('startup_complete')
""")
        self.assertEqual([record["event"] for record in records], ["startup_complete"])

    def test_lifecycle_emits_success_and_failure_events_without_exception_details(self):
        records = self.run_script("""
import asyncio
from types import SimpleNamespace
from unittest.mock import patch
from fastapi import FastAPI
from app.logging import configure_logging
from app.lifespan import lifespan
configure_logging()
app = FastAPI()
app.state.settings = SimpleNamespace(temp_image_dir='C:/private/photo.jpg')
async def check():
    with patch('app.lifespan.temporary_storage'), patch('app.lifespan.database_pool'):
        async with lifespan(app):
            pass
    with patch('app.lifespan.temporary_storage', side_effect=RuntimeError('Bearer secret-token')):
        try:
            async with lifespan(app):
                pass
        except RuntimeError:
            pass
asyncio.run(check())
""")
        self.assertEqual([record["event"] for record in records], [
            "startup_started", "startup_complete", "shutdown_started", "shutdown_complete",
            "startup_started", "startup_failed",
        ])


if __name__ == "__main__":
    unittest.main()
