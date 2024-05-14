
from motor.motor_asyncio import AsyncIOMotorClient
from icecream import ic
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import Message
from config import gpt_token
from openai import AsyncOpenAI
import logging
import asyncio
from mongo_gpt_connect import log_message_interaction

import tiktoken
encoding = tiktoken.encoding_for_model("gpt-4o")


main_router = Router()
client = AsyncOpenAI(api_key=gpt_token)


class Form(StatesGroup):
    default = State()


class User:
    def __init__(self, user_id):
        self.client = AsyncIOMotorClient('mongodb://localhost:27017')
        self.db = self.client.gpt_users
        self.users_collection = self.db.users
        self.user_id = str(user_id)

    async def create_user(self, initial_tokens=0, role='user'):
        user_doc = await self.users_collection.find_one({'_id': self.user_id})
        if not user_doc:
            result = await self.users_collection.insert_one({
                '_id': self.user_id,
                'token_balance': initial_tokens,
                'role': role
            })
            return True
        return False

    async def get_token_balance(self):
        try:
            user_doc = await self.users_collection.find_one({'_id': self.user_id})
            if user_doc:
                print(f"User document found: {user_doc}")  # Отладочный вывод
                return user_doc.get('token_balance', 0)
            else:
                print("No user document found")  # Отладочный вывод
                return 0
        except Exception as e:
            print(f"Error fetching user token balance: {e}")
            return None

    async def update_token_balance(self, tokens_used):
        try:
            if not isinstance(tokens_used, (int, float)):  # Проверка типа
                raise ValueError("tokens_used must be an integer or float")
            result = await self.users_collection.update_one(
                {'_id': self.user_id},
                {'$inc': {'token_balance': -tokens_used}}
            )
            # Отладочный вывод
            print(f"Tokens updated: {result.modified_count}")
            return result.modified_count
        except Exception as e:
            print(f"Error updating token balance: {e}")
            return 0

    async def set_token_balance(self, new_balance):
        try:
            if not isinstance(new_balance, (int, float)):  # Проверка типа
                raise ValueError("new_balance must be an integer or float")
            result = await self.users_collection.update_one(
                {'_id': self.user_id},
                {'$set': {'token_balance': new_balance}},
                upsert=True
            )
            # Отладочный вывод
            print(f"Token balance set: {result.modified_count}")
            return result.modified_count
        except Exception as e:
            print(f"Error setting new token balance: {e}")
            return 0


@main_router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    start_text = ('Привет, я бот, который подключен к API GPT-4, '
                  'я могу ответить тебе на любой вопрос, используя всю мощь искусственного интеллекта')
    await message.answer(text=start_text)


@main_router.message(Command('reset'))
async def handle_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(text='состояние сброшено')


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
    first_name = message.from_user.first_name
    username = message.from_user.username

    user = User(message.from_user.id)
    context_key = f"user_{user_id}"
    await user.create_user(initial_tokens=2000, role='user')

    # Получаем данные из состояния
    context_data = await state.get_data()
    user_data = context_data.get(context_key, {'assistant_id': None})

    if 'assistant_id' not in user_data:
        assistant = await create_assistant(client)
        if assistant is None:
            await message.answer("Failed to create an assistant.")
            return
        user_data['assistant_id'] = assistant.id

    if 'thread_id' not in user_data:
        thread = await client.beta.threads.create()
        if not thread:
            await message.answer("Failed to create a thread.")
            return
        user_data['thread_id'] = thread.id

    context_data[context_key] = user_data
    await state.set_data(context_data)

    await client.beta.threads.messages.create(
        thread_id=user_data['thread_id'],
        role="user",
        content=message.text
    )

    run = await client.beta.threads.runs.create(
        thread_id=user_data['thread_id'],
        assistant_id='asst_20LTOBd7QB8MOV09lzC1eD5X'
    )

    balance = await user.get_token_balance()
    print(f"Current token balance: {balance}")

    # Получение ответа ассистента и расчет токенов
    while True:
        run_response = await client.beta.threads.runs.retrieve(
            thread_id=user_data['thread_id'],
            run_id=run.id
        )
        if run_response.status in ['completed', 'failed']:

            context_data[context_key] = user_data
            await state.set_data(context_data)
            break
        await asyncio.sleep(0.3)

    messages_response = await client.beta.threads.messages.list(thread_id=user_data['thread_id'])
    gpt_response = None
    for msg in messages_response.data:
        if msg.role == 'assistant':
            gpt_response = msg.content[0].text.value
            break

    if gpt_response:
        user_input_tokens = len(encoding.encode(message.text))

        user_input = message.text

        assistant_response_tokens = len(encoding.encode(gpt_response))

        total_tokens_used = user_input_tokens + assistant_response_tokens

        print(f'total_tokens_used: {total_tokens_used}')
        await user.update_token_balance(tokens_used=int(total_tokens_used))

        new_balance = await user.get_token_balance()

        await message.answer(text=gpt_response, parse_mode="HTML")
        await log_message_interaction(user_id, username, first_name, user_input, gpt_response, user_input_tokens, assistant_response_tokens, total_tokens_used, new_balance)
    else:
        await message.answer(text="I currently don't work with this type of content 😔")
