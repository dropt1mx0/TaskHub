# keep_alive.py
# Простой HTTP-сервер в отдельном потоке — отвечает на пинги от Cron-Job.org.
# Mini App (aiohttp) запускается отдельно в основном asyncio loop (см. bot.py).

from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
import os


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"TaskHub is alive!")

    def log_message(self, *args):
        pass


def keep_alive():
    port = int(os.environ.get("KEEP_ALIVE_PORT", os.environ.get("PORT", 8080)))
    server = HTTPServer(("0.0.0.0", port), _Handler)
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"[keep_alive] Ping server started on port {port}")
