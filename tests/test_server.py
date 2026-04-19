from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from http import HTTPStatus

from cli_to_llm.server import handle_get, handle_post


class ServerTestCase(unittest.TestCase):
    def test_healthz(self) -> None:
        status, payload = handle_get("/healthz", default_model="test-model")
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["default_model"], "test-model")

    def test_simulate_endpoint(self) -> None:
        status, body = handle_post(
            "/simulate",
            {
                "client": "copilot",
                "prompt": "Create a Dockerfile for a local simulator",
            },
            default_model="test-model",
        )
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(body["client"], "copilot")
        self.assertEqual(body["task_type"], "code")


if __name__ == "__main__":
    unittest.main()
