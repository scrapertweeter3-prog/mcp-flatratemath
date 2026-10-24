import io
import json
import subprocess
import sys
import types
import unittest
from pathlib import Path

import server
from server import handle

SERVER = Path(__file__).with_name("server.py")


def frame(payload):
    """One stdio message: a single line of JSON, as the MCP stdio transport sends it."""
    return payload + b"\n"


def responses(raw):
    """Decode every line-delimited message a server run wrote out."""
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


class CostPerRequestValidationTests(unittest.TestCase):
    def _call(self, **arguments):
        return handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "cost_per_request", "arguments": arguments},
            }
        )

    def test_rejects_negative_rate(self):
        response = self._call(mode="flat", rate=-5995, months=12, requests=30)

        self.assertTrue(response["result"]["isError"])
        self.assertIn("rate must not be negative", response["result"]["content"][0]["text"])

    def test_rejects_zero_months(self):
        response = self._call(mode="flat", rate=5995, months=0, requests=30)

        self.assertTrue(response["result"]["isError"])
        self.assertIn("months must be at least 1", response["result"]["content"][0]["text"])

    def test_rejects_zero_requests(self):
        response = self._call(mode="flat", rate=5995, months=12, requests=0)

        self.assertTrue(response["result"]["isError"])
        self.assertIn("requests must be at least 1", response["result"]["content"][0]["text"])


class MalformedMessageTests(unittest.TestCase):
    def _read(self, raw):
        """Drive read_message() over raw bytes standing in for stdin."""
        original = sys.stdin
        sys.stdin = types.SimpleNamespace(buffer=io.BytesIO(raw))
        try:
            return server.read_message()
        finally:
            sys.stdin = original

    def _run(self, raw):
        """Run the server as a client would: lines in, lines out."""
        return subprocess.run(
            [sys.executable, str(SERVER)], input=raw, capture_output=True, timeout=30
        )

    def test_read_message_reports_a_malformed_body(self):
        with self.assertRaises(server.ParseError):
            self._read(frame(b"{oops"))

    def test_read_message_reports_a_body_that_is_not_utf8(self):
        with self.assertRaises(server.ParseError):
            self._read(frame(b'"\xff\xfe"'))

    def test_read_message_still_skips_framing_lines(self):
        """Blank lines and stray Content-Length headers are framing, not messages."""
        payload = b'{"jsonrpc": "2.0", "id": 7, "method": "ping"}'
        raw = b"\n" + b"Content-Length: 40\r\n" + frame(payload)

        self.assertEqual(self._read(raw), json.loads(payload))

    def test_bad_message_gets_a_parse_error_and_the_session_survives(self):
        raw = frame(b"{oops") + frame(b'{"jsonrpc": "2.0", "id": 2, "method": "ping"}')

        result = self._run(raw)

        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(
            responses(result.stdout),
            [
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"},
                },
                {"jsonrpc": "2.0", "id": 2, "result": {}},
            ],
        )

    def test_truncated_body_is_answered_before_the_stream_ends(self):
        result = self._run(b'{"jsonrpc": "2.0"')

        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(
            responses(result.stdout),
            [
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"},
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
