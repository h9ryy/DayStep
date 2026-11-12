import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.8):
        super().__init__()
        self.rate_limit = rate_limit
        self.last_actions: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id:
            now = time.monotonic()
            last_time = self.last_actions.get(user_id, 0.0)

            if now - last_time < self.rate_limit:
                if isinstance(event, CallbackQuery):
                    await event.answer("⏳ Не спешите, подождите секунду!", show_alert=False)
                return

            self.last_actions[user_id] = now

            # Периодическая очистка старых записей из памяти (если накопилось > 5000 юзеров)
            if len(self.last_actions) > 5000:
                threshold = now - 60.0
                self.last_actions = {k: v for k, v in self.last_actions.items() if v > threshold}

        return await handler(event, data)
