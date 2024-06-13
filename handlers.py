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
import openai
from openai import AsyncOpenAI
import logging
import asyncio
from mongo_gpt_connect import log_message_interaction
from bot import bot
import tiktoken
from config import mongodb_cient
from additional import split_message
from user_class import User
encoding = tiktoken.encoding_for_model("gpt-4o")


main_router = Router()



client = AsyncOpenAI(api_key=gpt_token)


class Form(StatesGroup):
    pay = State()
    default = State()


class Dalle(StatesGroup):

    dalle= State()



@main_router.message(Command('dalle'))
async def handle_switch_to_dalle(message: Message, state: FSMContext):
    print("handle_switch_to_dalle called")
    await state.set_state(Dalle.dalle)
    await message.answer('вы переключены в генератор изображений. Стоимость одной генерации 500 токенов!')
    ic(await state.get_state())




@main_router.message(Command('gpt'))
async def handle_switch_to_gpt(message: Message, state: FSMContext):
    print("handle_switch_to_dalle called")
    await state.set_state(Form.default)
    await message.answer('вы переключены в режим ChatGPT')
    ic(await state.get_state())

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





@main_router.message(StateFilter(Form.default), Command('new_dialog'))
#@main_router.message(Command('new_dialog'))
async def handle_start_new_dialog(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(text='Начат новый диалог')





@main_router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    user = User(message.from_user.id)
    await user.create_user(initial_tokens=4000, role='user')

    balance = await user.get_token_balance()
    start_text = (f'Привет, я бот, который подключен к API GPT-4o, '
                  f'я могу ответить тебе на любой вопрос, используя всю мощь искусственного интеллекта'
                  f'твой баланс {balance} токенов')

    await message.answer(text=start_text)
    await state.clear()

@main_router.message(F.successful_payment, StateFilter(Form.pay))
async def successful_payment(message: Message, state: FSMContext):
    print("successful_payment called")

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





@main_router.message(Command('balance'))
async def handle_balance(message: Message, state: FSMContext):
    user = User(message.from_user.id)
    balance = await user.get_token_balance()
    await message.answer(text=f'Ваш баланс {int(balance)} токенов')





@main_router.message(~StateFilter(Form.default), StateFilter(Dalle.dalle))
#@main_router.message(F.text, StateFilter(Dalle.dalle))
async def handle_dalle_text(message: Message, state: FSMContext):
    print('сработал handle_dalle_text')
    user = User(message.from_user.id)
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    openai.api_key = gpt_token
    balance = await user.get_token_balance()
    if balance > 0:
        print(f"Current token balance: {balance}")
        response = openai.images.generate(
            model="dall-e-3",
            prompt=message.text,
            n=1,
            size="1024x1024",
            quality= "hd"
        )

        image_url = response.data[0].url

        await message.answer_photo(photo=image_url)
        await user.update_token_balance(tokens_used=500)
        await log_message_interaction(user_id, username, first_name, user_input=message.text,
                                      gpt_response=image_url, user_input_tokens=0, assistant_response_tokens=500,
                                      total_tokens_used=500, new_balance=balance+500)
    else:
        await message.answer(f'Ваш баланс {int(balance)} токенов, пополните его чтобы сгенерировать изображение')




@main_router.message(~StateFilter(Dalle.dalle), F.text, ~StateFilter(Form.pay))
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
    user_data = context_data.get(context_key, {'assistant_id': None, 'thread_id': None})

    messages_before_reset = await user.get_msg_count()
    ic(messages_before_reset)

    if messages_before_reset > 5:
        user_data['thread_id'] = 0

    # Проверка и создание нового thread, если не существует
    if user_data.get('thread_id') is None:
        thread = await client.beta.threads.create()
        if not thread:
            await message.answer("Failed to create a thread.")
            return
        user_data['thread_id'] = thread.id

    context_data[context_key] = user_data
    ic(context_data[context_key])
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
            messages = await split_message(gpt_response)
            messages_before_reset += 1
            user.update_msg_count(msg_count=messages_before_reset)
            for msg in messages:
                await message.answer(text=msg, parse_mode='Markdown')
            await log_message_interaction(user_id, username, first_name, user_input, gpt_response, user_input_tokens, assistant_response_tokens, total_tokens_used, new_balance)
        else:
            await message.answer(text="I currently don't work with this type of content 😔")
    else:
        await message.answer(text=f'ваш баланс {int(balance)} токенов. Для продолжения пополните счет '
                             f'с помощью команды /pay_100 или /pay_300', parse_mode='Markdown')
