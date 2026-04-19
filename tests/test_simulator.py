from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cli_to_llm.simulator import (
    SimulationRequest,
    build_chat_completion,
    detect_language,
    detect_task_type,
    simulate_response,
)


class SimulatorTestCase(unittest.TestCase):
    def test_detects_code_task(self) -> None:
        self.assertEqual(detect_task_type("Create a Docker compose file"), "code")

    def test_detects_debug_task(self) -> None:
        self.assertEqual(detect_task_type("App failed with a traceback"), "debug")

    def test_detects_language(self) -> None:
        self.assertEqual(detect_language("Write a YAML config for docker compose"), "yaml")

    def test_copilot_response_is_concise(self) -> None:
        response = simulate_response(
            SimulationRequest(client="copilot", prompt="Create a bash script for a health check")
        )
        self.assertEqual(response["client"], "copilot")
        self.assertIn("Starter implementation", response["content"])
        self.assertIn("```bash", response["content"])

    def test_claude_response_is_structured(self) -> None:
        response = simulate_response(
            SimulationRequest(client="claude", prompt="Create a python function to parse JSON")
        )
        self.assertEqual(response["client"], "claude")
        self.assertIn("Why this shape:", response["content"])
        self.assertIn("```python", response["content"])

    def test_build_chat_completion_uses_model_hint(self) -> None:
        response = build_chat_completion(
            {
                "model": "claude-sim-v1",
                "messages": [{"role": "user", "content": "Explain the architecture"}],
            }
        )
        self.assertEqual(response["simulation"]["client"], "claude")
        self.assertEqual(response["choices"][0]["message"]["role"], "assistant")


if __name__ == "__main__":
    unittest.main()
