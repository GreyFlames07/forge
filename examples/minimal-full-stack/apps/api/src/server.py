from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._write(200, {"status": "ok"})
            return
        if self.path == "/api/dashboard":
            self._write(200, {"message": "hello from minimal full stack"})
            return
        if self.path == "/api/profile":
            self._write(200, {"full_name": "Forge Example", "tier": "starter"})
            return
        self._write(404, {"error": "not_found"})

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _write(self, status: int, payload: dict[str, str]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    server = HTTPServer(("127.0.0.1", 8000), Handler)
    print("minimal-full-stack api listening on http://127.0.0.1:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
