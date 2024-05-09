from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import Message
from test_gpt import query_gpt4
from config import gpt_token
from openai import AsyncOpenAI


main_router = Router()




@main_router.message(F.text)
async def handle_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_message = message.text
    client = AsyncOpenAI(api_key=gpt_token)

    # Получаем историю контекста пользователя из состояния
    context_history = await state.get_data()
    if 'thread_id' not in context_history:
        thread = await client.beta.threads.create()
        thread_id = thread.id
        messages = []
        await state.update_data(thread_id=thread_id, messages=messages)
    else:
        thread_id = context_history['thread_id']
        messages = context_history['messages']

    # Append the new user message to the context messages
    messages.append(user_message)

    # Call the function to query GPT-4
    response, tokens = await query_gpt4(user_message, user_id, messages, thread_id)

    # Update the state with the new message and response
    messages.append(response)
    await state.update_data(messages=messages)

    # Respond to the user
    await message.answer(response)

