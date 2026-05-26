import asyncio
import threading
from typing import Any

from telegram import Bot


class Publisher:
    def __init__(self, bot_token: str, chat_id: str, logger: Any = None) -> None:
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id
        self.logger = logger
        self.loop = asyncio.new_event_loop()
        self._lock = threading.Lock()
        self._initialized = False

    async def _send(self, message: str) -> None:
        if not self._initialized:
            await self.bot.initialize()
            self._initialized = True

        await self.bot.send_message(
            chat_id=self.chat_id,
            text=message[:4096],
            parse_mode="HTML",
        )

    async def _close(self) -> None:
        if self._initialized:
            await self.bot.shutdown()
            self._initialized = False

    def publish(self, message: str) -> bool:
        if self.logger:
            self.logger.info("Publishing message to Telegram")

        try:
            with self._lock:
                self.loop.run_until_complete(self._send(message))
            if self.logger:
                self.logger.info("Telegram publish succeeded")
            return True
        except Exception:
            if self.logger:
                self.logger.exception("Telegram publish failed")
            return False

    def close(self) -> None:
        try:
            with self._lock:
                if not self.loop.is_closed():
                    self.loop.run_until_complete(self._close())
                    self.loop.close()
        except Exception:
            if self.logger:
                self.logger.exception("Failed to close Telegram publisher")
