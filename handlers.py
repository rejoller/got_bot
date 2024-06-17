from aiogram.types import PreCheckoutQuery,  LabeledPrice, successful_payment, SuccessfulPayment, CallbackQuery
from motor.motor_asyncio import AsyncIOMotorClient
from icecream import ic
from aiogram import types, Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandStart, StateFilter, CommandObject
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

    dalle = State()


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


@main_router.message(Command('pay_1'))
@main_router.message(Command('pay_10'))
@main_router.message(Command('pay_50'))
@main_router.message(Command('pay_100'))
@main_router.message(Command('pay_500'))
async def handle_payment(message: Message, command=CommandObject):
    print("handle_payment called")
    amount = int(command.command.split("_")[1])

    try:

        prices = [LabeledPrice(label="XTR", amount=amount)]
        invoice_description = f"Покупка {amount*1000} токенов за {amount} stars"
        await message.answer_invoice(
            title=f"Покупка {amount} stars",
            description=invoice_description,
            payload="100_stars",
            provider_token="",
            currency="XTR",
            prices=prices,
            start_parameter="start_parameter_here"
        )
    except Exception as e:
        print(f"Error in handle_payment: {e}")


@main_router.message(StateFilter(Form.default), Command('new_dialog'))
async def handle_start_new_dialog(message: Message, state: FSMContext):
    user = User(message.from_user.id)
    await state.clear()
    await user.update_msg_count(msg_count=0)
    await message.answer(text='Начат новый диалог')


@main_router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    user = User(message.from_user.id)
    await user.create_user(initial_tokens=4000, role='user')

    balance = await user.get_token_balance()
    start_text = (
        f"Добро пожаловать! / Welcome!\n\n"
        f"Этот бот предоставляет доступ к двум мощным AI инструментам. Chat-GPT4 позволяет вам общаться "
        f"с передовой моделью обработки естественного языка, а Dalle-3 генерирует уникальные изображения по "
        f"вашим текстовым запросам. Вся валюта в боте представлена в формате telegram stars.\n\n"
        f"This bot provides access to two powerful AI tools. Chat-GPT4 lets you converse with an advanced "
        f"language model, while Dalle-3 generates unique images from your text prompts. All currency in the "
        f"bot is represented in telegram stars.\n\n"
        f"Команды:\n"
        f"Commands:\n\n"
        f"/new_dialog - Новый диалог / Start a new dialog\n"
        f"/gpt - Режим ChatGPT / Switch to ChatGPT mode\n"
        f"/dalle - Режим генерации изображений Dalle-3 / Dalle-3 image generation mode\n"
        f"/pay_1 - Купить 1 000 токенов / Top up the account with 1,000 tokens\n"
        f"/pay_10 - Купить 10 000 токенов / Top up the account with 10,000 tokens\n"
        f"/pay_50 - Купить 50 000 токенов / Top up the account with 50,000 tokens\n"
        f"/pay_100 - Купить 100 000 токенов / Top up the account with 100,000 tokens\n"
        f"/pay_500 - Купить 500 000 токенов / Top up the account with 500,000 tokens\n"
        f"/balance - Текущий баланс / Check the current balance\n\n"
        f"Ваш текущий баланс - {balance} токенов / Your current balance - {balance} tokens\n\n"
    )

    await message.answer(text=start_text)
    await state.clear()


@main_router.message(F.successful_payment, StateFilter(Form.pay))
async def successful_payment(message: Message, state: FSMContext):
    print("successful_payment called")

    amount = 0
    invoice_sum_user = message.successful_payment.total_amount

    if invoice_sum_user <= 110:
        amount = invoice_sum_user
        ic(amount)

    if 110 < invoice_sum_user <= 310:
        amount = invoice_sum_user*1.2
        ic(amount)

    user = User(message.from_user.id)

    await user.increase_token_balance(amount)
    new_balance = await user.get_token_balance()
    await message.answer(f"Баланс успешно пополнен на {amount * 1000} токенов!"
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
# @main_router.message(F.text, StateFilter(Dalle.dalle))
async def handle_dalle_text(message: Message, state: FSMContext):
    print('сработал handle_dalle_text')
    user = User(message.from_user.id)


    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    openai.api_key = gpt_token
    balance = await user.get_token_balance()
    if balance > 0:
        await bot.send_chat_action(action='upload_photo', chat_id = user_id)
        print(f"Current token balance: {balance}")
        response = openai.images.generate(
            model="dall-e-3",
            prompt=message.text,
            n=1,
            size="1024x1024",
            quality="hd"
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
    user_data = context_data.get(
        context_key, {'assistant_id': None, 'thread_id': None})

    messages_before_reset = await user.get_msg_count()
    ic(messages_before_reset)

    if user_data.get('thread_id') is None or messages_before_reset > 10:
        user_data['thread_id'] = None
        messages_before_reset = 0
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
        await bot.send_chat_action(action='typing', chat_id = user_id)
        while True:
            run_response = await client.beta.threads.runs.retrieve(
                thread_id=user_data['thread_id'],
                run_id=run.id
            )
            if run_response.status in ['completed', 'failed']:

                context_data[context_key] = user_data
                await state.set_data(context_data)
                break
            await asyncio.sleep(0.2)

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
            await user.update_msg_count(msg_count=messages_before_reset)
            for msg in messages:
                await message.answer(text=msg, parse_mode='Markdown')
            await log_message_interaction(user_id, username, first_name, user_input, gpt_response, user_input_tokens, assistant_response_tokens, total_tokens_used, new_balance)
        else:
            await message.answer(text="I currently don't work with this type of content 😔")
    else:
        await message.answer(text=f'ваш баланс {int(balance)} токенов. Для продолжения пополните счет '
                             f'с помощью команды /pay_100 или /pay_300', parse_mode='Markdown')
