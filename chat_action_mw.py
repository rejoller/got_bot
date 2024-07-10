from aiogram import BaseMiddleware
from aiogram.dispatcher.flags import get_flag
from aiogram.utils.chat_action import ChatActionSender
from typing import Any, Callable, Dict, Awaitable
from aiogram.types import Message


class ChatActionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        long_operation_type = get_flag(data, "long_operation")
        bot = data.get('bot')  # Получаем объект бота из данных

        if not long_operation_type:
            return await handler(event, data)

        # Если флаг есть
        async with ChatActionSender(
                action=long_operation_type,
                chat_id=event.chat.id,
                bot=bot  # Передаем объект бота
        ):
            return await handler(event, data)
