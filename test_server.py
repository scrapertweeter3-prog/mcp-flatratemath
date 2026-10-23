import unittest

from server import handle


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


if __name__ == "__main__":
    unittest.main()
