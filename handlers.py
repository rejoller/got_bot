from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import Message
from test_gpt import query_gpt4
from config import gpt_token
from openai import AsyncOpenAI
import logging
import asyncio
main_router = Router()

client = AsyncOpenAI(api_key=gpt_token)



class Form(StatesGroup):
    default = State()



from icecream import ic


async def create_assistant(client):
    try:
        assistant = await client.beta.assistants.create(
            name="Math tutor",
            instructions="You are a personal math tutor. Write and run code to answer math questions",
            tools=[{"type": "code_interpreter"}],
            model="gpt-4"
        )
        ic(assistant)
        return assistant
    except Exception as e:
        logging.error(f"Error creating assistant: {str(e)}")
        return None

@main_router.message(F.text)
async def handle_text(message: Message, state: FSMContext):

    await state.set_state(Form.default)
    user_id = message.from_user.id
    context_key = f"user_{user_id}"

    # Получаем данные из состояния
    context_data = await state.get_data()
    ic(context_data)

    user_data = context_data.get(context_key, {'assistant_id': None})
    ic(user_data)

    # Проверяем наличие ассистента и создаем при необходимости
    if 'assistant_id' not in user_data:
        assistant = await create_assistant(client)
        if assistant is None:
            await message.answer("Failed to create an assistant.")
            return
        assistant_id = assistant.id
        user_data['assistant_id'] = assistant_id
        ic(assistant_id)

    # Проверяем наличие thread_id, создаем если нет и сохраняем в контекст
    if 'thread_id' not in user_data:
        thread = await client.beta.threads.create()
        if not thread:
            await message.answer("Failed to create a thread.")
            return
        thread_id = thread.id
        user_data['thread_id'] = thread_id
        ic(thread_id)

    # Обновляем данные состояния для пользователя
    context_data[context_key] = user_data
    await state.set_data(context_data)
    ic(await state.get_data())  # Проверяем обновленные данные

    # Создание сообщения в потоке
    await client.beta.threads.messages.create(
        thread_id=user_data['thread_id'],
        role="user",
        content=message.text
    )

    # Запуск выполнения в потоке с использованием ассистента
    run = await client.beta.threads.runs.create(
        thread_id=user_data['thread_id'],
        assistant_id='asst_20LTOBd7QB8MOV09lzC1eD5X' # Использование assistant_id из данных пользователя
    )
    ic(run)

    # Получение ответа ассистента
    while True:
        run_response = await client.beta.threads.runs.retrieve(
            thread_id=user_data['thread_id'],
            run_id=run.id
        )
        
        if run_response.status in ['completed', 'failed']:
            break
        await asyncio.sleep(0.3)  # Пауза для ожидания обновления статуса запроса

    # Получение сообщений после завершения run
    messages_response = await client.beta.threads.messages.list(thread_id=user_data['thread_id'])
   
    gpt_response = None  # Инициализация переменной для хранения последнего текста
    # Обработка и вывод сообщений
    for msg in messages_response.data:
        if msg.role == 'assistant':
            gpt_response = msg.content[0].text.value
            print("Assistant:", gpt_response)
            break
        else:
            print(f"{msg.role}: [Message content not available or not text]")

    if gpt_response:
        await message.answer(text=gpt_response)
    else:
        await message.answer(text='я пока не работаю с таким контентом 😔')
    if gpt_response:
        print("Последнее сообщение ассистента:", gpt_response)
    else:
        print("No assistant messages found.")


   
    









