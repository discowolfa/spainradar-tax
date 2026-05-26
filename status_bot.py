import asyncio
import threading
from html import escape
from pathlib import Path
from typing import Callable, Optional

from telegram import Bot

from config import DATABASE_PATH


class StatusState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data = {
            "last_cycle_at": "не было",
            "fetched": 0,
            "new": 0,
            "published": 0,
            "errors": 0,
            "db_count": 0,
            "db_size_kb": 0,
        }

    def update(self, **kwargs) -> None:
        with self._lock:
            self._data.update(kwargs)

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._data)


class StatusCommandBot:
    def __init__(
        self,
        bot_token: str,
        status_chat_id: str,
        get_status_text: Callable[[], str],
        logger=None,
    ) -> None:
        self.bot = Bot(token=bot_token)
        self.status_chat_id = str(status_chat_id)
        self.get_status_text = get_status_text
        self.logger = logger
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        asyncio.run(self._poll())

    async def _poll(self) -> None:
        offset = None
        await self.bot.initialize()

        try:
            while not self._stop_event.is_set():
                try:
                    updates = await self.bot.get_updates(
                        offset=offset,
                        timeout=10,
                        allowed_updates=["message", "channel_post"],
                    )

                    for update in updates:
                        offset = update.update_id + 1
                        message = update.effective_message
                        if not message or not message.text:
                            continue

                        chat_id = str(message.chat_id)
                        if chat_id != self.status_chat_id:
                            continue

                        command = message.text.strip().split()[0].lower()
                        if command not in {"/status", "/health"}:
                            continue

                        await self.bot.send_message(
                            chat_id=message.chat_id,
                            text=self.get_status_text(),
                            parse_mode="HTML",
                        )
                except Exception:
                    if self.logger:
                        self.logger.exception("Status command polling failed")
                    await asyncio.sleep(5)
        finally:
            await self.bot.shutdown()


def format_status_text(state: dict) -> str:
    db_path = Path(DATABASE_PATH)
    db_size_kb = db_path.stat().st_size // 1024 if db_path.exists() else 0

    return (
        "<b>SpainRadar Tax: статус</b>\n\n"
        f"Последний цикл: {escape(str(state.get('last_cycle_at', 'не было')))}\n"
        f"Получено из RSS: {int(state.get('fetched', 0))}\n"
        f"Новых найдено: {int(state.get('new', 0))}\n"
        f"Опубликовано: {int(state.get('published', 0))}\n"
        f"Ошибок: {int(state.get('errors', 0))}\n"
        f"База: {int(state.get('db_count', 0))} записей, {db_size_kb} KB"
    )
