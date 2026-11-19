import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

__author__ = "@anhafxd"

SITE_FOLDER = Path(__file__).parent / "fixture_site"
TEMPLATED_SUFFIXES = {".html", ".xml", ".txt"}
REDIRECT_ROUTES = {
    "/old-page": (301, "/about.html"),
    "/chain-start": (301, "/chain-middle"),
    "/chain-middle": (302, "/about.html"),
    "/loop-a": (302, "/loop-b"),
    "/loop-b": (302, "/loop-a"),
}
STATUS_ROUTES = {"/server-error": 500}


@dataclass(frozen=True)
class FixtureSite:
    origin: str
    external_origin: str

    def url(self, path: str) -> str:
        return f"{self.origin}{path}"


class FixtureHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, directory=str(SITE_FOLDER), **kwargs)

    def origins(self) -> tuple[str, str]:
        port = self.server.server_address[1]
        return f"http://127.0.0.1:{port}", f"http://localhost:{port}"

    def send_simple(self, status: int, body: bytes, content_type: str, head_only: bool) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def answer(self, head_only: bool) -> None:
        path = self.path.split("?", 1)[0]
        if path in REDIRECT_ROUTES:
            status, location = REDIRECT_ROUTES[path]
            self.send_response(status)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path in STATUS_ROUTES:
            self.send_simple(STATUS_ROUTES[path], b"boom", "text/plain", head_only)
            return
        local_file = SITE_FOLDER / path.lstrip("/")
        if local_file.is_dir():
            local_file = local_file / "index.html"
        if (
            local_file.suffix in TEMPLATED_SUFFIXES
            and local_file.is_file()
            and path.endswith((".html", ".xml", ".txt", "/"))
        ):
            origin, external_origin = self.origins()
            text = local_file.read_text(encoding="utf-8")
            text = text.replace("__EXTERNAL_ORIGIN__", external_origin)
            text = text.replace("__ORIGIN__", origin)
            content_type = self.guess_type(str(local_file))
            self.send_simple(200, text.encode("utf-8"), content_type, head_only)
            return
        if head_only:
            super().do_HEAD()
        else:
            super().do_GET()

    def do_GET(self) -> None:
        self.answer(head_only=False)

    def do_HEAD(self) -> None:
        self.answer(head_only=True)

    def log_message(self, format: str, *args: object) -> None:
        return None


@contextmanager
def serve_fixture_site() -> Iterator[FixtureSite]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        yield FixtureSite(f"http://127.0.0.1:{port}", f"http://localhost:{port}")
    finally:
        server.shutdown()
        server.server_close()
