# keep_alive.py
# Запускает Mini App веб-сервер в фоновом потоке.
# На Render: Cron-Job.org пингует корневой URL "/" каждую минуту — Render не усыпит сервис.
# Этот же сервер обслуживает Telegram Mini App (API + фронтенд).

import asyncio
import os
from threading import Thread


def keep_alive():
    """Запустить aiohttp Mini App сервер в отдельном потоке."""
    port = int(os.environ.get("PORT", 8080))

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        from webapp.server import create_app
        from aiohttp import web

        app = create_app()
        web.run_app(app, host="0.0.0.0", port=port, print=lambda *_: None)

    thread = Thread(target=_run, daemon=True)
    thread.start()
    print(f"[keep_alive] Mini App server started on port {port}")
