#!/usr/bin/env python3
"""Rank VLESS links by end-to-end health, latency, and download speed."""

from __future__ import annotations

import concurrent.futures
import http.client
import json
import os
import statistics
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import socket
import ssl
from pathlib import Path
from typing import Any, Callable

from collector import extract_vless, identity_key, with_remark


ROOT = Path(__file__).resolve().parent
OUTPUT_FILE = ROOT / "pure.txt"
HEALTH_URLS = (
    "https://cp.cloudflare.com/generate_204",
    "https://www.google.com/generate_204",
    "https://www.gstatic.com/generate_204",
)
SPEED_URL = "https://speed.cloudflare.com/__down?bytes=131072"
SUPPORTED_NETWORKS = {"tcp", "ws", "grpc", "http", "httpupgrade", "xhttp"}
SUPPORTED_SECURITY = {"none", "tls", "reality"}
DOWNLOAD_BYTES = 128 * 1024
MAX_SOURCE_BYTES = 64 * 1024 * 1024


def _value(query: dict[str, list[str]], *keys: str, default: str = "") -> str:
    for key in keys:
        values = query.get(key)
        if values:
            return values[0]
    return default


def _boolean(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _hosts(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def outbound_from_uri(uri: str) -> dict[str, Any] | None:
    """Convert a common VLESS share link into an Xray outbound object."""
    try:
        parsed = urllib.parse.urlsplit(uri)
        if parsed.scheme.lower() != "vless" or not parsed.hostname or not parsed.port:
            return None
        user_id = urllib.parse.unquote(parsed.username or "")
        if not user_id:
            return None
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    except ValueError:
        return None

    network = _value(query, "type", "network", "transport", default="tcp").lower()
    network = {"websocket": "ws", "h2": "http", "splithttp": "xhttp"}.get(network, network)
    security = _value(query, "security", default="none").lower()
    if network not in SUPPORTED_NETWORKS or security not in SUPPORTED_SECURITY:
        return None

    user: dict[str, Any] = {
        "id": user_id,
        "encryption": _value(query, "encryption", default="none") or "none",
        "level": 0,
    }
    flow = _value(query, "flow")
    if flow:
        user["flow"] = flow

    stream: dict[str, Any] = {"network": network, "security": security}
    server_name = _value(query, "sni", "serverName") or _value(query, "host")

    if security == "tls":
        tls: dict[str, Any] = {}
        if server_name:
            tls["serverName"] = server_name
        fingerprint = _value(query, "fp", "fingerprint")
        if fingerprint:
            tls["fingerprint"] = fingerprint
        alpn = _hosts(_value(query, "alpn"))
        if alpn:
            tls["alpn"] = alpn
        insecure = _value(query, "allowInsecure", "allowinsecure")
        if insecure:
            tls["allowInsecure"] = _boolean(insecure)
        stream["tlsSettings"] = tls
    elif security == "reality":
        public_key = _value(query, "pbk", "publicKey")
        if not public_key:
            return None
        reality: dict[str, Any] = {
            "show": False,
            "fingerprint": _value(query, "fp", "fingerprint", default="chrome") or "chrome",
            "publicKey": public_key,
        }
        if server_name:
            reality["serverName"] = server_name
        short_id = _value(query, "sid", "shortId")
        if short_id:
            reality["shortId"] = short_id
        spider_x = _value(query, "spx", "spiderX")
        if spider_x:
            reality["spiderX"] = spider_x
        stream["realitySettings"] = reality

    path = _value(query, "path", default="/") or "/"
    host = _value(query, "host", "authority")
    if network == "ws":
        settings: dict[str, Any] = {"path": path}
        if host:
            settings["headers"] = {"Host": host}
        early_data = _value(query, "ed")
        if early_data.isdigit():
            settings["maxEarlyData"] = int(early_data)
        early_header = _value(query, "eh")
        if early_header:
            settings["earlyDataHeaderName"] = early_header
        stream["wsSettings"] = settings
    elif network == "grpc":
        settings = {"serviceName": _value(query, "serviceName", "service_name", "s")}
        if host:
            settings["authority"] = host
        settings["multiMode"] = _value(query, "mode").lower() == "multi"
        stream["grpcSettings"] = settings
    elif network == "http":
        settings = {"path": path}
        hosts = _hosts(host)
        if hosts:
            settings["host"] = hosts
        stream["httpSettings"] = settings
    elif network == "httpupgrade":
        settings = {"path": path}
        if host:
            settings["host"] = host
        stream["httpupgradeSettings"] = settings
    elif network == "xhttp":
        settings = {"path": path}
        if host:
            settings["host"] = host
        mode = _value(query, "mode")
        if mode:
            settings["mode"] = mode
        stream["xhttpSettings"] = settings
    elif network == "tcp":
        header_type = _value(query, "headerType", "header_type", default="none").lower()
        if header_type == "http":
            headers: dict[str, list[str]] = {"User-Agent": ["Mozilla/5.0"]}
            hosts = _hosts(host)
            if hosts:
                headers["Host"] = hosts
            stream["tcpSettings"] = {
                "header": {
                    "type": "http",
                    "request": {
                        "version": "1.1",
                        "method": "GET",
                        "path": [path],
                        "headers": headers,
                    },
                }
            }

    return {
        "tag": "proxy",
        "protocol": "vless",
        "settings": {
            "vnext": [
                {
                    "address": parsed.hostname,
                    "port": parsed.port,
                    "users": [user],
                }
            ]
        },
        "streamSettings": stream,
    }


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            raise OSError("SOCKS proxy closed the connection")
        chunks.extend(chunk)
    return bytes(chunks)


def _socks_connect(proxy_port: int, host: str, port: int, timeout: float) -> socket.socket:
    sock = socket.create_connection(("127.0.0.1", proxy_port), timeout=timeout)
    try:
        sock.sendall(b"\x05\x01\x00")
        if _recv_exact(sock, 2) != b"\x05\x00":
            raise OSError("Xray SOCKS authentication negotiation failed")
        host_bytes = host.encode("idna")
        if len(host_bytes) > 255:
            raise OSError("Target hostname is too long")
        sock.sendall(b"\x05\x01\x00\x03" + bytes([len(host_bytes)]) + host_bytes + port.to_bytes(2, "big"))
        reply = _recv_exact(sock, 4)
        if reply[0] != 5 or reply[1] != 0:
            raise OSError(f"Xray could not connect through VLESS (SOCKS status {reply[1]})")
        if reply[3] == 1:
            _recv_exact(sock, 4)
        elif reply[3] == 3:
            _recv_exact(sock, _recv_exact(sock, 1)[0])
        elif reply[3] == 4:
            _recv_exact(sock, 16)
        else:
            raise OSError("Invalid SOCKS address type")
        _recv_exact(sock, 2)
        return sock
    except Exception:
        sock.close()
        raise


def https_get_via_xray(
    proxy_port: int,
    url: str,
    timeout: float,
    download_bytes: int = 0,
) -> tuple[float, float]:
    """Return request latency and, when requested, measured download Mbps."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError(f"Health-check URL must be HTTPS: {url}")
    host = parsed.hostname
    port = parsed.port or 443
    target = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
    started = time.monotonic()
    raw = _socks_connect(proxy_port, host, port, timeout)
    secure = None
    connection = None
    try:
        secure = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
        connection = http.client.HTTPSConnection(host, port=port, timeout=timeout)
        connection.sock = secure
        connection.request(
            "GET",
            target,
            headers={
                "User-Agent": "VLESS-Pure-Health-Check/1.0",
                "Accept-Encoding": "identity",
                "Connection": "close",
            },
        )
        response = connection.getresponse()
        elapsed = max(time.monotonic() - started, 0.001)
        if response.status < 200 or response.status >= 300:
            raise OSError(f"HTTPS test returned HTTP {response.status}")
        if not download_bytes:
            return elapsed * 1000, 0.0
        body = response.read(download_bytes)
        transfer_time = max(time.monotonic() - started, 0.001)
        if len(body) < min(download_bytes, 16 * 1024):
            raise OSError("Speed-test endpoint returned too little data")
        return elapsed * 1000, (len(body) * 8) / transfer_time / 1_000_000
    finally:
        if connection is not None:
            connection.close()
        elif secure is not None:
            secure.close()
        else:
            raw.close()


def _wait_for_socks(proc: subprocess.Popen[Any], proxy_port: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False
        try:
            with socket.create_connection(("127.0.0.1", proxy_port), timeout=0.2):
                return True
        except OSError:
            time.sleep(0.05)
    return False


def _with_xray(
    xray_bin: str,
    uri: str,
    request: Callable[[int], Any],
) -> Any:
    outbound = outbound_from_uri(uri)
    if outbound is None:
        return None
    proxy_port = _free_port()
    config = {
        "log": {"loglevel": "none"},
        "inbounds": [
            {
                "listen": "127.0.0.1",
                "port": proxy_port,
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": False},
            }
        ],
        "outbounds": [outbound],
    }
    with tempfile.TemporaryDirectory(prefix="pure-xray-") as temp_dir:
        config_path = Path(temp_dir) / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        try:
            proc = subprocess.Popen(
                [xray_bin, "run", "-c", str(config_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            return None
        try:
            if not _wait_for_socks(proc, proxy_port, float(os.getenv("XRAY_START_TIMEOUT", "8"))):
                return None
            return request(proxy_port)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


def health_probe(xray_bin: str, uri: str) -> dict[str, Any]:
    latencies: list[float] = []

    def check(proxy_port: int) -> None:
        for url in HEALTH_URLS:
            try:
                latency, _ = https_get_via_xray(
                    proxy_port,
                    url,
                    float(os.getenv("PROXY_TIMEOUT", "5")),
                )
                latencies.append(latency)
            except (OSError, TimeoutError, ssl.SSLError, http.client.HTTPException, ValueError):
                continue

    _with_xray(xray_bin, uri, check)
    return {
        "uri": uri,
        "health_successes": len(latencies),
        "health_total": len(HEALTH_URLS),
        "latency_ms": round(statistics.median(latencies), 2) if latencies else 0.0,
    }


def speed_probe(xray_bin: str, uri: str) -> dict[str, Any]:
    def check(proxy_port: int) -> float:
        _latency, speed = https_get_via_xray(
            proxy_port,
            SPEED_URL,
            float(os.getenv("SPEED_TIMEOUT", "12")),
            DOWNLOAD_BYTES,
        )
        return speed

    try:
        speed = _with_xray(xray_bin, uri, check)
    except (OSError, TimeoutError, ssl.SSLError, http.client.HTTPException, ValueError):
        speed = None
    return {"uri": uri, "speed_mbps": round(float(speed or 0), 3)}


def rank_score(result: dict[str, Any]) -> float:
    """Balance repeated health success, measured throughput, and response latency."""
    quality = result["health_successes"] / result["health_total"]
    latency = max(float(result["latency_ms"]), 1.0)
    speed = max(float(result.get("speed_mbps", 0.0)), 0.0)
    return quality * speed / (1.0 + latency / 100.0)


def _parallel(
    values: list[str],
    worker: Callable[[str], dict[str, Any]],
    workers: int,
    label: str,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(worker, value) for value in values]
        for completed, future in enumerate(concurrent.futures.as_completed(futures), 1):
            try:
                results.append(future.result())
            except Exception as error:
                print(f"WARN {label} worker failed: {error}")
            if completed % 250 == 0 or completed == len(futures):
                print(f"{label}: {completed}/{len(futures)} completed")
    return results


def _read_candidates() -> list[str]:
    source_url = os.getenv("VLESS_SOURCE_URL", "").strip()
    if source_url:
        request = urllib.request.Request(
            source_url,
            headers={"User-Agent": "VLESS-Pure-Ranker/1.0", "Accept": "text/plain,*/*;q=0.5"},
        )
        with urllib.request.urlopen(request, timeout=40) as response:
            payload = response.read(MAX_SOURCE_BYTES + 1)
        if len(payload) > MAX_SOURCE_BYTES:
            raise ValueError("VLESS source exceeded the 64 MiB safety limit")
        text = payload.decode("utf-8", errors="replace")
    else:
        text = (ROOT / "vless.txt").read_text(encoding="utf-8")

    candidates: list[str] = []
    seen: set[tuple[object, ...]] = set()
    for uri in extract_vless(text):
        key = identity_key(uri)
        if key not in seen:
            seen.add(key)
            candidates.append(uri)
    return candidates[: max(1, int(os.getenv("MAX_CONFIGS", "50000")))]


def rank_configs(
    candidates: list[str],
    xray_bin: str,
    *,
    workers: int = 64,
    speed_candidates: int = 3000,
    top_n: int = 2000,
    probe: Callable[[str], dict[str, Any]] | None = None,
    speed_test: Callable[[str], dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    health_worker = probe or (lambda uri: health_probe(xray_bin, uri))
    speed_worker = speed_test or (lambda uri: speed_probe(xray_bin, uri))
    health = _parallel(candidates, health_worker, workers, "Health")
    healthy = [item for item in health if item["health_successes"] >= 2]
    healthy.sort(key=lambda item: (-item["health_successes"], item["latency_ms"]))
    to_speed_test = healthy[: max(1, speed_candidates)]

    speeds = _parallel([item["uri"] for item in to_speed_test], speed_worker, workers, "Speed")
    speed_by_uri = {item["uri"]: item["speed_mbps"] for item in speeds}
    ranked: list[dict[str, Any]] = []
    for item in to_speed_test:
        enriched = {**item, "speed_mbps": speed_by_uri.get(item["uri"], 0.0)}
        if enriched["speed_mbps"] > 0:
            enriched["score"] = rank_score(enriched)
            ranked.append(enriched)
    ranked.sort(
        key=lambda item: (
            -item["score"],
            -item["health_successes"],
            item["latency_ms"],
            -item["speed_mbps"],
        )
    )
    return ranked[: max(1, top_n)], {
        "candidates": len(candidates),
        "health_passed": len(healthy),
        "speed_tested": len(to_speed_test),
        "speed_passed": len(ranked),
    }


def write_output(results: list[dict[str, Any]], output_file: Path = OUTPUT_FILE) -> None:
    if not results:
        raise RuntimeError("No VLESS nodes passed health and speed checks; previous pure.txt was kept")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = output_file.with_name(f".{output_file.name}.tmp")
    temporary_file.write_text(
        "".join(f"{with_remark(item['uri'])}\n" for item in results),
        encoding="utf-8",
    )
    temporary_file.replace(output_file)


def main() -> int:
    started = time.monotonic()
    try:
        candidates = _read_candidates()
        if not candidates:
            raise RuntimeError("The VLESS source contained no supported configurations")
        results, stats = rank_configs(
            candidates,
            os.getenv("XRAY_BIN", "xray"),
            workers=int(os.getenv("PURE_WORKERS", "64")),
            speed_candidates=int(os.getenv("SPEED_CANDIDATES", "3000")),
            top_n=int(os.getenv("TOP_N", "2000")),
        )
        write_output(results)
    except (OSError, RuntimeError, ValueError, urllib.error.URLError) as error:
        print(f"ERROR: pure ranking failed: {error}")
        return 1

    stats.update(
        {
            "published": len(results),
            "elapsed_seconds": round(time.monotonic() - started, 2),
            "median_latency_ms": round(statistics.median(item["latency_ms"] for item in results), 2),
            "median_speed_mbps": round(statistics.median(item["speed_mbps"] for item in results), 3),
        }
    )
    print(json.dumps(stats, indent=2))
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        summary = "\n".join(
            [
                "## Pure VLESS ranking",
                "",
                f"- Candidates health-tested: {stats['candidates']}",
                f"- Passed 2+ of {len(HEALTH_URLS)} HTTPS checks: {stats['health_passed']}",
                f"- Download-speed tested: {stats['speed_tested']}",
                f"- Published to `pure.txt`: {stats['published']}",
                f"- Median latency: {stats['median_latency_ms']} ms",
                f"- Median download speed: {stats['median_speed_mbps']} Mbps",
                f"- Runtime: {stats['elapsed_seconds']} s",
                "",
                "Rank score = health success ratio x download Mbps / (1 + latency ms / 100).",
            ]
        )
        with open(summary_path, "a", encoding="utf-8") as summary_file:
            summary_file.write(summary + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
