import asyncio
from contextlib import contextmanager
from datetime import datetime
import io
import json
import logging
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app import observability as obs


@contextmanager
def capture_events(level="DEBUG"):
    stream = io.StringIO()
    # Capture somente a camada CineData, sem absorver avisos do asyncio/Uvicorn.
    with patch("app.observability.sys", SimpleNamespace(stderr=stream)):
        obs.configure_logging(level)
        try:
            yield stream
        finally:
            obs.configure_logging("INFO")
    obs.configure_logging("INFO")


def events(stream):
    return [json.loads(line) for line in stream.getvalue().splitlines()]


class LoggingTests(unittest.TestCase):
    def test_json_level_and_repeated_configuration(self):
        external = logging.getLogger("httpx").level
        with capture_events("INFO") as stream:
            for _ in range(3):
                obs.configure_logging("INFO")
            obs.log_event(logging.DEBUG, "schema_loaded", duration_ms=1)
            obs.log_event(logging.INFO, "app_started", configured=True)
            obs.configure_logging("DEBUG")
            obs.log_event(logging.DEBUG, "schema_loaded", duration_ms=2)
        rows = events(stream)
        self.assertEqual(
            [row["event"] for row in rows], ["app_started", "schema_loaded"]
        )
        self.assertEqual(rows[0]["level"], "INFO")
        self.assertEqual(rows[0]["logger"], "cinedata")
        self.assertIsNone(rows[0]["request_id"])
        self.assertIsNotNone(datetime.fromisoformat(rows[0]["timestamp"]).utcoffset())
        self.assertEqual(logging.getLogger("httpx").level, external)

    def test_invalid_level_has_constant_warning(self):
        with capture_events() as stream:
            obs.configure_logging("SECRET-LEVEL")
            obs.log_event(logging.DEBUG, "schema_loaded", duration_ms=1)
            obs.log_event(logging.INFO, "app_started", configured=False)
        self.assertEqual(
            [r["event"] for r in events(stream)], ["log_level_invalid", "app_started"]
        )
        self.assertNotIn("SECRET-LEVEL", stream.getvalue())

    def test_allowlist_rejects_arbitrary_objects_and_non_finite_numbers(self):
        with capture_events() as stream:
            obs.log_event(
                logging.INFO,
                "sql_finished",
                duration_ms=float("nan"),
                rows=float("inf"),
                truncado=True,
                sql="SECRET-SQL",
                parametros={"key": "SECRET-VALUE"},
                prompt=object(),
            )
            obs.log_event(
                logging.INFO,
                "model_request_started",
                call_number=1,
                model="gsk-SECRET-KEY",
            )
            obs.log_event(
                logging.INFO,
                "model_request_started",
                call_number=2,
                model="bad\nSECRET-MODEL",
            )
            obs.log_event(logging.INFO, "SECRET-EVENT", question="SECRET-QUESTION")
        rows = events(stream)
        self.assertIsNone(rows[0]["duration_ms"])
        self.assertIsNone(rows[0]["rows"])
        self.assertTrue(rows[0]["truncado"])
        self.assertIsNone(rows[1]["model"])
        self.assertIsNone(rows[2]["model"])
        self.assertEqual(len(rows), 3)
        self.assertNotIn("SECRET", stream.getvalue())

    def test_exception_and_cause_never_appear_even_in_debug(self):
        try:
            try:
                raise ValueError("SECRET-CAUSE")
            except ValueError as cause:
                raise RuntimeError("SECRET-EXCEPTION") from cause
        except RuntimeError as error:
            with capture_events() as stream:
                obs.log_event(
                    logging.ERROR,
                    "request_failed",
                    code="erro_inesperado",
                    **obs.error_metadata(error),
                )
        row = events(stream)[0]
        self.assertEqual(row["exception_type"], "RuntimeError")
        self.assertTrue(row["frames"])
        self.assertEqual(set(row["frames"][0]), {"file", "function", "line"})
        self.assertNotIn("SECRET", stream.getvalue())
        self.assertNotIn("raise RuntimeError", stream.getvalue())
        with capture_events("INFO") as stream:
            obs.log_event(
                logging.ERROR,
                "request_failed",
                **obs.error_metadata(RuntimeError("SECRET")),
            )
        self.assertNotIn("frames", events(stream)[0])

    def test_extreme_numeric_fields_cannot_break_logging(self):
        with capture_events() as stream:
            obs.log_event(logging.INFO, "sql_finished", rows=10**1000, duration_ms=-1)
        row = events(stream)[0]
        self.assertIsNone(row["rows"])
        self.assertIsNone(row["duration_ms"])

    def test_unconfigured_cli_does_not_emit_unformatted_events(self):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import logging; from app.observability import log_event; log_event(logging.WARNING, 'sql_rejected', category='read_only')",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stderr, "")

    def test_credential_like_model_names_are_omitted(self):
        with capture_events() as stream:
            for name in (
                "gsk_SECRET_KEY",
                "GSK_SECRET_KEY",
                "sk_SECRET_KEY",
                "gsk-SECRET-KEY",
                "sk-SECRET-KEY",
            ):
                obs.log_event(logging.INFO, "app_started", configured=True, model=name)
                obs.log_event(
                    logging.INFO, "model_request_started", call_number=1, model=name
                )
            obs.log_event(
                logging.INFO,
                "model_request_started",
                call_number=1,
                model="openai/gpt-oss-120b",
            )
        rows = events(stream)
        self.assertTrue(all(row["model"] is None for row in rows[:-1]))
        self.assertEqual(rows[-1]["model"], "openai/gpt-oss-120b")
        self.assertNotIn("SECRET", stream.getvalue())


class ContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_context_isolated_in_tasks_threads_and_restored_on_exception(self):
        ready = asyncio.Event()
        entered = 0

        async def operation(request_id):
            nonlocal entered
            with obs.request_context(request_id):
                entered += 1
                if entered == 2:
                    ready.set()
                await ready.wait()
                obs.log_event(logging.INFO, "question_received", question_chars=7)
                await asyncio.to_thread(
                    obs.log_event, logging.DEBUG, "schema_loaded", duration_ms=1
                )
                with obs.request_context("nested"):
                    self.assertEqual(obs.current_context().request_id, "nested")
                self.assertEqual(obs.current_context().request_id, request_id)
                raise RuntimeError("SECRET")

        with capture_events() as stream:
            results = await asyncio.gather(
                operation("first"), operation("second"), return_exceptions=True
            )
            self.assertTrue(all(isinstance(result, RuntimeError) for result in results))
            self.assertIsNone(obs.current_context())
            obs.log_event(logging.INFO, "app_stopped")
        rows = events(stream)
        for request_id in ("first", "second"):
            self.assertEqual(
                {r["event"] for r in rows if r["request_id"] == request_id},
                {"question_received", "schema_loaded"},
            )
        self.assertIsNone(rows[-1]["request_id"])
