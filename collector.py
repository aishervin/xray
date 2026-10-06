#!/usr/bin/env python3
"""Collect public VLESS links, deduplicate them, and keep TCP-reachable nodes."""

from __future__ import annotations

import base64
import concurrent.futures
import html
import http.client
import ipaddress
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Iterable


ROOT = Path(__file__).resolve().parent
SOURCE_FILE = ROOT / "source" / "source.txt"
OUTPUT_FILE = ROOT / "vless.txt"
REMARK = "☬ T.me/aiShervin"
SUPPORTED_TRANSPORTS = {"ws", "websocket", "grpc", "xhttp",}
REALITY_TRANSPORTS = SUPPORTED_TRANSPORTS | {"tcp"}
MAX_SOURCE_BYTES = 8 * 1024 * 1024
VLESS_PATTERN = re.compile(r"vless://[^\s\"'<>`\\]+", re.IGNORECASE)
BASE64_LINE_PATTERN = re.compile(r"^[A-Za-z0-9_+/=-]{16,}$")


def read_sources(path: Path = SOURCE_FILE) -> list[str]:
    """Read HTTPS source URLs, one per line; blank lines and comments are ignored."""
    sources: list[str] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parsed = urllib.parse.urlsplit(line)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError(f"Source line {line_number} must be an HTTPS URL: {line}")
        sources.append(line)
    return sources


def fetch_source(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "VLESS-Hourly-Collector/1.0", "Accept": "text/plain,*/*;q=0.5"},
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        payload = response.read(MAX_SOURCE_BYTES + 1)
    if len(payload) > MAX_SOURCE_BYTES:
        raise ValueError(f"Source exceeded {MAX_SOURCE_BYTES} bytes")
    return payload.decode("utf-8", errors="replace")


def _decoded_payloads(text: str) -> Iterable[str]:
    """Yield the response and decoded whole-list or per-line Base64 subscriptions."""
    current = html.unescape(text).strip()
    for _ in range(2):
        yield current
        decoded_lines = []
        for line in current.splitlines():
            value = _decode_base64(line.strip())
            if value and "vless://" in value.lower():
                decoded_lines.append(value)
        decoded = "\n".join(decoded_lines)
        if not decoded:
            compact = "".join(current.split())
            decoded = _decode_base64(compact)
            if decoded and "vless://" not in decoded.lower():
                decoded = None
        if not decoded or decoded == current:
            return
        current = decoded


def _decode_base64(value: str) -> str | None:
    if not value or not BASE64_LINE_PATTERN.fullmatch(value):
        return None
    try:
        padded = value + "=" * (-len(value) % 4)
        return base64.b64decode(padded, altchars=b"-_", validate=True).decode("utf-8").strip()
    except (ValueError, UnicodeDecodeError):
        return None


def _clean_uri(value: str) -> str:
    uri = html.unescape(value.strip())
    while uri and uri[-1] in ".,;!)]}":
        uri = uri[:-1]
    return uri


def _valid_vless_uri(uri: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(uri)
        return (
            parsed.scheme.lower() == "vless"
            and bool(parsed.username)
            and bool(parsed.hostname)
            and parsed.port is not None
            and 1 <= parsed.port <= 65535
        )
    except ValueError:
        return False


def _is_supported_transport(uri: str) -> bool:
    parsed = urllib.parse.urlsplit(uri)
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    security = query.get("security", [""])[0].lower()
    transport = query.get("type", query.get("transport", query.get("network", ["tcp"])))[0].lower()
    return (security == "reality" and transport in REALITY_TRANSPORTS) or transport in SUPPORTED_TRANSPORTS


def extract_vless(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for payload in _decoded_payloads(text):
        for match in VLESS_PATTERN.findall(payload):
            uri = _clean_uri(match)
            if _valid_vless_uri(uri) and _is_supported_transport(uri) and uri not in seen:
                found.append(uri)
                seen.add(uri)
    return found


def identity_key(uri: str) -> tuple[object, ...]:
    """Identify a node without its display name or query parameter order."""
    parsed = urllib.parse.urlsplit(uri)
    query = tuple(sorted(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)))
    return (
        parsed.scheme.lower(),
        (parsed.username or "").lower(),
        parsed.hostname.lower() if parsed.hostname else "",
        parsed.port,
        parsed.path,
        query,
    )


def with_remark(uri: str) -> str:
    parsed = urllib.parse.urlsplit(uri)
    return urllib.parse.urlunsplit(parsed._replace(fragment=REMARK))


def tcp_reachable(uri: str, timeout: float = 3.5) -> bool:
    """Return whether a public IP for the VLESS endpoint accepts a TCP connection."""
    parsed = urllib.parse.urlsplit(uri)
    host, port = parsed.hostname, parsed.port
    if not host or not port:
        return False
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError:
        return False

    for family, socktype, protocol, _canonical_name, sockaddr in addresses:
        try:
            address = ipaddress.ip_address(sockaddr[0].split("%", 1)[0])
        except ValueError:
            continue
        if not address.is_global:
            continue
        try:
            with socket.socket(family, socktype, protocol) as connection:
                connection.settimeout(timeout)
                connection.connect(sockaddr)
            return True
        except OSError:
            continue
    return False


def collect(
    sources: list[str],
    output_file: Path,
    *,
    fetcher: Callable[[str], str] = fetch_source,
    tcp_checker: Callable[[str], bool] | None = None,
    workers: int = 64,
    max_configs: int = 10_000,
) -> dict[str, int | float]:
    started = time.monotonic()
    stats: dict[str, int | float] = {
        "sources": len(sources),
        "sources_ok": 0,
        "sources_failed": 0,
        "raw_vless": 0,
        "duplicates": 0,
        "tcp_tested": 0,
        "tcp_failed": 0,
        "published": 0,
    }
    unique: list[str] = []
    seen_keys: set[tuple[object, ...]] = set()

    for source in sources:
        try:
            payload = fetcher(source)
        except (OSError, ValueError, urllib.error.URLError, TimeoutError, http.client.HTTPException) as error:
            print(f"WARN source failed: {source}: {error}", file=sys.stderr)
            stats["sources_failed"] += 1
            continue
        stats["sources_ok"] += 1
        uris = extract_vless(payload)
        stats["raw_vless"] += len(uris)
        for uri in uris:
            key = identity_key(uri)
            if key in seen_keys:
                stats["duplicates"] += 1
                continue
            seen_keys.add(key)
            unique.append(uri)

    candidates = unique[:max_configs]
    if stats["sources_ok"] == 0:
        raise RuntimeError("All configured sources failed; keeping the existing subscription")
    if not candidates and output_file.exists() and output_file.read_text(encoding="utf-8").strip():
        raise RuntimeError("No supported VLESS entries were found; keeping the existing subscription")

    checker = tcp_checker or (lambda uri: tcp_reachable(uri, float(os.getenv("TCP_TIMEOUT", "3.5"))))
    worker_count = max(1, workers)
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        reachable = [uri for uri, alive in zip(candidates, executor.map(checker, candidates)) if alive]

    stats["tcp_tested"] = len(candidates)
    stats["tcp_failed"] = len(candidates) - len(reachable)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = output_file.with_name(f".{output_file.name}.tmp")
    temporary_file.write_text("".join(f"{with_remark(uri)}\n" for uri in reachable), encoding="utf-8")
    temporary_file.replace(output_file)
    stats["published"] = len(reachable)
    stats["elapsed_seconds"] = round(time.monotonic() - started, 2)
    return stats


def main() -> int:
    try:
        sources = read_sources()
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if not sources:
        print(f"ERROR: no HTTPS sources found in {SOURCE_FILE}", file=sys.stderr)
        return 1

    try:
        stats = collect(
            sources,
            OUTPUT_FILE,
            workers=int(os.getenv("TCP_WORKERS", "64")),
            max_configs=int(os.getenv("MAX_CONFIGS", "10000")),
        )
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: collection failed: {error}", file=sys.stderr)
        return 1

    print(json.dumps(stats, indent=2))
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        summary = "\n".join(
            [
                "## VLESS collection",
                "",
                f"- Sources: {stats['sources']} ({stats['sources_failed']} failed)",
                f"- Unique candidates TCP-tested: {stats['tcp_tested']}",
                f"- TCP-unreachable: {stats['tcp_failed']}",
                f"- Published: {stats['published']}",
                f"- Runtime: {stats['elapsed_seconds']} s",
            ]
        )
        with open(summary_path, "a", encoding="utf-8") as summary_file:
            summary_file.write(summary + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
