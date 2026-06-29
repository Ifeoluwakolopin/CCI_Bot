import json
import os
import platform
import resource
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class HealthSnapshot:
    def __init__(self, mongo_client: Any) -> None:
        self.mongo_client = mongo_client
        self.started_at = time.monotonic()
        self._last_wall = self.started_at
        self._last_cpu = time.process_time()
        self._lock = threading.Lock()

    def build(self) -> tuple[HTTPStatus, dict[str, Any]]:
        mongo_ok = self._mongo_ok()
        body = {
            "status": "ok" if mongo_ok else "unhealthy",
            "version": os.getenv("APP_VERSION", "unknown"),
            "uptime_seconds": round(time.monotonic() - self.started_at, 3),
            "checks": {"mongo": mongo_ok},
            "resources": {
                "cpu_percent": self._cpu_percent(),
                "mem_bytes": _rss_bytes(),
                "mem_percent": _memory_percent(),
            },
        }
        return (HTTPStatus.OK if mongo_ok else HTTPStatus.SERVICE_UNAVAILABLE, body)

    def _mongo_ok(self) -> bool:
        try:
            self.mongo_client.admin.command("ping")
        except Exception:
            return False
        return True

    def _cpu_percent(self) -> float:
        with self._lock:
            now = time.monotonic()
            cpu_now = time.process_time()
            elapsed = now - self._last_wall
            cpu_elapsed = cpu_now - self._last_cpu
            self._last_wall = now
            self._last_cpu = cpu_now

        if elapsed <= 0:
            return 0.0
        return round(max(0.0, (cpu_elapsed / elapsed) * 100), 2)


def _rss_bytes() -> int:
    statm_path = Path("/proc/self/statm")
    if statm_path.exists():
        try:
            resident_pages = int(statm_path.read_text(encoding="utf-8").split()[1])
            return resident_pages * os.sysconf("SC_PAGE_SIZE")
        except (OSError, IndexError, ValueError):
            pass

    max_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        return max_rss
    return max_rss * 1024


def _memory_percent() -> float:
    total_memory = _total_memory_bytes()
    if not total_memory:
        return 0.0
    return round((_rss_bytes() / total_memory) * 100, 2)


def _total_memory_bytes() -> int | None:
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, OSError, ValueError):
        return None


def _health_enabled() -> bool:
    return os.getenv("HEALTH_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


def _handler(snapshot: HealthSnapshot) -> type[BaseHTTPRequestHandler]:
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if urlparse(self.path).path != "/health":
                self.send_error(HTTPStatus.NOT_FOUND)
                return

            status, body = snapshot.build()
            payload = json.dumps(body, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    return HealthHandler


def start_health_server(
    mongo_client: Any, logger: Any = None
) -> ThreadingHTTPServer | None:
    if not _health_enabled():
        return None

    host = os.getenv("HEALTH_HOST", "0.0.0.0")
    port = int(os.getenv("HEALTH_PORT", "8080"))
    server = ThreadingHTTPServer((host, port), _handler(HealthSnapshot(mongo_client)))
    thread = threading.Thread(
        target=server.serve_forever,
        name="health-server",
        daemon=True,
    )
    thread.start()

    if logger:
        logger.info("Health endpoint listening on %s:%s/health", host, port)

    return server
