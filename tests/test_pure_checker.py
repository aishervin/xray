import tempfile
import unittest
from pathlib import Path

from pure_checker import outbound_from_uri, rank_configs, rank_score, write_output


class PureCheckerTests(unittest.TestCase):
    def test_builds_reality_websocket_outbound(self):
        uri = (
            "vless://1234@example.com:443?type=ws&security=reality&sni=cdn.example"
            "&fp=chrome&pbk=public-key&sid=abcd&spx=%2F&host=front.example"
            "&path=%2Fsocket&ed=128&eh=Sec-WebSocket-Protocol#node"
        )
        outbound = outbound_from_uri(uri)
        self.assertIsNotNone(outbound)
        assert outbound is not None
        stream = outbound["streamSettings"]
        self.assertEqual(stream["network"], "ws")
        self.assertEqual(stream["security"], "reality")
        self.assertEqual(stream["realitySettings"]["publicKey"], "public-key")
        self.assertEqual(stream["realitySettings"]["serverName"], "cdn.example")
        self.assertEqual(stream["wsSettings"]["headers"]["Host"], "front.example")
        self.assertEqual(stream["wsSettings"]["maxEarlyData"], 128)

    def test_builds_tls_grpc_outbound(self):
        uri = (
            "vless://1234@example.com:443?type=grpc&security=tls&sni=grpc.example"
            "&alpn=h2%2Chttp%2F1.1&serviceName=svc&authority=front.example&mode=multi"
        )
        outbound = outbound_from_uri(uri)
        self.assertIsNotNone(outbound)
        assert outbound is not None
        stream = outbound["streamSettings"]
        self.assertEqual(stream["tlsSettings"]["alpn"], ["h2", "http/1.1"])
        self.assertEqual(stream["grpcSettings"]["serviceName"], "svc")
        self.assertEqual(stream["grpcSettings"]["authority"], "front.example")
        self.assertTrue(stream["grpcSettings"]["multiMode"])

    def test_rejects_invalid_or_unsupported_uri(self):
        self.assertIsNone(outbound_from_uri("not a vless link"))
        self.assertIsNone(outbound_from_uri("vless://id@example.com:443?security=unknown"))
        self.assertIsNone(outbound_from_uri("vless://id@example.com:443?security=reality"))

    def test_rank_score_rewards_speed_and_reliability(self):
        fast = {"health_successes": 3, "health_total": 3, "latency_ms": 50, "speed_mbps": 12}
        flaky = {"health_successes": 2, "health_total": 3, "latency_ms": 50, "speed_mbps": 12}
        self.assertGreater(rank_score(fast), rank_score(flaky))

    def test_filters_health_failures_and_returns_top_ranked(self):
        candidates = ["slow", "fast", "flaky", "dead"]
        health = {
            "slow": {"uri": "slow", "health_successes": 3, "health_total": 3, "latency_ms": 120},
            "fast": {"uri": "fast", "health_successes": 3, "health_total": 3, "latency_ms": 40},
            "flaky": {"uri": "flaky", "health_successes": 2, "health_total": 3, "latency_ms": 30},
            "dead": {"uri": "dead", "health_successes": 1, "health_total": 3, "latency_ms": 10},
        }
        speeds = {"slow": 8.0, "fast": 10.0, "flaky": 10.0}
        ranked, stats = rank_configs(
            candidates,
            "unused",
            workers=2,
            speed_candidates=3,
            top_n=2,
            probe=health.__getitem__,
            speed_test=lambda uri: {"uri": uri, "speed_mbps": speeds[uri]},
        )
        self.assertEqual([item["uri"] for item in ranked], ["fast", "flaky"])
        self.assertEqual(stats["health_passed"], 3)
        self.assertEqual(stats["speed_passed"], 3)

    def test_writes_only_ranked_uris_with_clean_remark(self):
        results = [
            {"uri": "vless://one@example.com:443?type=tcp#old"},
            {"uri": "vless://two@example.com:443?type=tcp#old"},
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "pure.txt"
            write_output(results, output)
            self.assertEqual(
                output.read_text(encoding="utf-8").splitlines(),
                [
                    "vless://one@example.com:443?type=tcp#T.me/aShervin",
                    "vless://two@example.com:443?type=tcp#T.me/aShervin",
                ],
            )


if __name__ == "__main__":
    unittest.main()
