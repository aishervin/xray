import base64
import tempfile
import unittest
from pathlib import Path

from collector import (
    collect,
    extract_vless,
    identity_key,
    read_sources,
    with_remark,
)


class CollectorTests(unittest.TestCase):
    def test_extracts_supported_transports_and_reality(self):
        content = "\n".join(
            [
                "vless://id1@example.com:443?type=ws&security=tls&sni=ssl.example&host=edge.example#old",
                "vless://id2@example.com:443?type=grpc&security=tls&sni=grpc.example&serviceName=svc",
                "vless://id3@example.com:443?type=xhttp&security=none&sni=edge.example",
                "vless://id4@example.com:443?type=http&security=tls&sni=edge.example",
                "vless://id5@example.com:443?type=tcp&security=reality&pbk=key&flow=xtls-rprx-vision&sni=edge.example",
                "vless://id6@example.com:443?type=tcp&security=tls&sni=edge.example",
                "vless://id7@example.com:443?type=tcp&security=reality&pbk=key&sni=edge.example",
                "vless://id8@example.com:443?type=xhttp&security=reality&pbk=key&sni=edge.example&mode=auto&encryption=mlkem768x25519plus.native.0rtt.key",
                "vless://id9@example.com:80?type=ws&security=tls&sni=ssl.example&host=edge.example",
            ]
        )
        nodes = extract_vless(content)
        self.assertEqual(
            nodes,
            [
                "vless://id1@example.com:443?type=ws&security=tls&sni=ssl.example&host=edge.example#old",
                "vless://id2@example.com:443?type=grpc&security=tls&sni=grpc.example&serviceName=svc",
                "vless://id5@example.com:443?type=tcp&security=reality&pbk=key&flow=xtls-rprx-vision&sni=edge.example",
                "vless://id8@example.com:443?type=xhttp&security=reality&pbk=key&sni=edge.example&mode=auto&encryption=mlkem768x25519plus.native.0rtt.key",
            ],
        )

    def test_extracts_base64_subscription(self):
        source = "vless://id@example.com:443?type=grpc&security=tls&sni=grpc.example#source"
        encoded = base64.b64encode(source.encode()).decode()
        self.assertEqual(extract_vless(encoded), [source])

    def test_extracts_individually_base64_encoded_lines(self):
        sources = [
            "vless://one@example.com:443?type=ws&security=tls&sni=ssl.example&host=edge.example",
            "vless://two@example.com:443?type=xhttp&security=tls&sni=edge.example",
        ]
        encoded = "\n".join(base64.b64encode(item.encode()).decode() for item in sources)
        self.assertEqual(extract_vless(encoded), sources)

    def test_deduplicates_parameter_order_and_remark(self):
        first = "vless://ABC@Example.com:443?type=ws&security=tls&path=%2F#first"
        second = "vless://abc@example.com:443?path=%2F&security=tls&type=ws#second"
        self.assertEqual(identity_key(first), identity_key(second))

    def test_replaces_remark_exactly(self):
        result = with_remark("vless://id@example.com:443?type=ws#old%20name")
        self.assertEqual(
            result,
            "vless://id@example.com:443?type=ws#%E2%98%AC%20T.me%2FaiShervin",
        )

    def test_rejects_non_https_source(self):
        with tempfile.TemporaryDirectory() as directory:
            sources_file = Path(directory) / "sources.txt"
            sources_file.write_text("http://example.com/list.txt\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_sources(sources_file)

    def test_collects_deduplicates_probes_and_writes_only_live_nodes(self):
        contents = {
            "https://feed.example/one": "\n".join(
                [
                    "vless://one@example.com:443?type=ws&security=tls&sni=ssl.example&host=edge.example#name1",
                    "vless://two@example.com:443?type=grpc&security=tls&sni=grpc.example#name2",
                ]
            ),
            "https://feed.example/two": "vless://ONE@example.com:443?sni=ssl.example&host=edge.example&security=tls&type=ws#duplicate",
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "vless.txt"
            stats = collect(
                list(contents),
                output,
                fetcher=contents.__getitem__,
                tcp_checker=lambda uri: "one@" in uri,
                workers=2,
            )
            lines = output.read_text(encoding="utf-8").splitlines()
        self.assertEqual(stats["duplicates"], 1)
        self.assertEqual(stats["tcp_tested"], 2)
        self.assertEqual(stats["published"], 1)
        self.assertEqual(
            lines,
            [
                "vless://one@example.com:443?type=ws&security=tls&sni=ssl.example&host=edge.example"
                "#%E2%98%AC%20T.me%2FaiShervin"
            ],
        )

    def test_keeps_previous_output_when_every_source_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "vless.txt"
            output.write_text("previous subscription\n", encoding="utf-8")

            def fail(_url):
                raise OSError("offline")

            with self.assertRaises(RuntimeError):
                collect(["https://feed.example/list"], output, fetcher=fail)
            self.assertEqual(output.read_text(encoding="utf-8"), "previous subscription\n")


if __name__ == "__main__":
    unittest.main()
