from aiogram.types import PreCheckoutQuery,  LabeledPrice, successful_payment, SuccessfulPayment, CallbackQuery
from motor.motor_asyncio import AsyncIOMotorClient
from icecream import ic
from aiogram import types, Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import Message
from config import TOKEN_YOOKASSA, gpt_token
from openai import AsyncOpenAI
import logging
import asyncio
from mongo_gpt_connect import log_message_interaction
from bot import bot
import tiktoken
from config import mongodb_cient
encoding = tiktoken.encoding_for_model("gpt-4o")


main_router = Router()
client = AsyncOpenAI(api_key=gpt_token)


class Form(StatesGroup):
    pay = State()
    default = State()


class User:
    def __init__(self, user_id):
        self.client_mongo = mongodb_cient
        self.db = self.client_mongo.gpt_users
        self.users_collection = self.db.users
        self.user_id = str(user_id)

    async def create_user(self, initial_tokens=2000, role='user'):
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

                return user_doc['token_balance']
            else:
                print("No user document found")
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
                {'$inc': {'token_balance': -tokens_used}},
                upsert=True
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

    async def increase_token_balance(self, amount):
        try:
            tokens_to_add = amount * 500
            result = await self.users_collection.update_one(
                {'_id': self.user_id},
                {'$inc': {'token_balance': tokens_to_add}},
                upsert=True
            )
            print(
                f"Token balance increased by {tokens_to_add}: {result.modified_count}")
            return result.modified_count
        except Exception as e:
            print(f"Error increasing token balance: {e}")
            return 0


@main_router.message(Command('pay_100'))
async def handle_payment(message: Message):
    print("handle_payment called")

    try:
        # 100 рублей (в копейках)
        prices = [LabeledPrice(label='Пополнение баланса', amount=10000)]
        await message.bot.send_invoice(
            chat_id=message.from_user.id,
            title='Пополнить баланс',
            description='Пополнение баланса на 50 000 токенов',
            payload='add_balance',
            provider_token=TOKEN_YOOKASSA,
            currency='rub',
            prices=prices,
            start_parameter='test',
            need_email=True
        )
        print("Invoice sent")
    except Exception as e:
        print(f"Error in handle_payment: {e}")


@main_router.message(Command('pay_300'))
async def handle_payment(message: Message):
    print("handle_payment called")
    total_amount = 30000
    try:
        # 100 рублей (в копейках)
        prices = [LabeledPrice(
            label='Пополнение баланса', amount=total_amount)]
        await message.bot.send_invoice(
            chat_id=message.from_user.id,
            title='Пополнить баланс',
            description='Пополнение баланса на 180 000 токенов',
            payload='add_balance',
            provider_token=TOKEN_YOOKASSA,
            currency='rub',
            prices=prices,
            start_parameter='test',
            need_email=True
        )
        print("Invoice sent")
    except Exception as e:
        print(f"Error in handle_payment: {e}")


@main_router.message(F.successful_payment, StateFilter(Form.pay))
async def successful_payment(message: Message, state: FSMContext):
    print("successful_payment called")
    current_state = await state.get_state()
    amount = 0
    invoice_sum_user = message.successful_payment.total_amount/100

    if invoice_sum_user <= 110:
        amount = invoice_sum_user
        ic(amount)


    if 110 < invoice_sum_user <= 310:
        amount = invoice_sum_user*1.2
        ic(amount)
 

 
    print(f"Payment info: {amount}")
    user = User(message.from_user.id)

    await user.increase_token_balance(amount)
    new_balance = await user.get_token_balance()
    await message.answer(f"Баланс успешно пополнен на {amount * 500} токенов!"
                            f"\nНа вашем счету {new_balance} токенов")

    await state.set_state(Form.default)
    print("Balance updated and message sent")



@main_router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, bot: Bot, state: FSMContext):
    print("process_pre_checkout_query called")
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
    await state.set_state(Form.pay)
    current_state = await state.get_state()
    print(f"Current state: {current_state}")

'''
@main_router.message(F.successful_payment, StateFilter(Form.pay))
async def successful_payment(message: Message, state: FSMContext):
    print("successful_payment called")
    current_state = await state.get_state()
    print(f"Current state at successful_payment: {current_state}")
    try:
        amount = message.successful_payment.total_amount/100
        print(f"Payment info: {amount}")
        user = User(message.from_user.id)

        await user.increase_token_balance(amount)
        new_balance = await user.get_token_balance()
        await message.answer(f"Баланс успешно пополнен на {amount * 50} токенов!"
                             f"\nНа вашем счету {new_balance} токенов") 
        
        await state.set_state(Form.default)
        print("Balance updated and message sent")
    except Exception as e:
        print(f"Error in successful_payment: {e}")
'''


@main_router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    user = User(message.from_user.id)
    await user.create_user(initial_tokens=4000, role='user')
    balance = await user.get_token_balance()
    start_text = (f'Привет, я бот, который подключен к API GPT-4o, '
                  f'я могу ответить тебе на любой вопрос, используя всю мощь искусственного интеллекта'
                  f'твой баланс {balance} токенов')

    await message.answer(text=start_text)


@main_router.message(Command('balance'))
async def handle_balance(message: Message, state: FSMContext):
    user = User(message.from_user.id)
    balance = await user.get_token_balance()
    await message.answer(text=f'Ваш баланс {balance} токенов')


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


@main_router.message(F.text, ~StateFilter(Form.pay))
async def handle_text(message: Message, state: FSMContext):
    print('сработал handle_text')
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

    if balance > 0:
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

            await message.answer(text=gpt_response, parse_mode='HTML')
            await log_message_interaction(user_id, username, first_name, user_input, gpt_response, user_input_tokens, assistant_response_tokens, total_tokens_used, new_balance)
        else:
            await message.answer(text="I currently don't work with this type of content 😔")
    else:
        await message.answer(text=f'ваш баланс {balance} токенов. Для продолжения пополните счет '
                             f'с помощью команды /pay_100 или /pay_300', parse_mode='HTML')
