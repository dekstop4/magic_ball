import asyncio
import logging
from datetime import datetime
from typing import Optional

from ollama import Client
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from database import init_db, save_conversation

BOT_TOKEN = "8011350529:AAG6lDcaNm_dfpi-2hpFkBy4Fa_TyRbLshw"
OLLAMA_API_KEY = "98fd824932524c85bdb873f338371466.ARdmopbEhoOt2PGlyLskKlHu"
OLLAMA_HOST = "https://ollama.com"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
ZODIAC_SIGNS = {
    "Овен": {
        "dates": [(3, 21), (4, 19)],
        "stereotype": "импульсивный, энергичный лидер, который действует прежде чем думает. "
                      "Нетерпеливый, прямолинейный, любит соревнования и побеждать."
    },
    "Телец": {
        "dates": [(4, 20), (5, 20)],
        "stereotype": "упрямый материалист, любит комфорт, еду и стабильность. "
                      "Медлительный, но надёжный, ценит роскошь и красивые вещи."
    },
    "Близнецы": {
        "dates": [(5, 21), (6, 20)],
        "stereotype": "болтливый и непостоянный, имеет много интересов но ни в чём не эксперт. "
                      "Любопытный, общительный, легко меняет мнение."
    },
    "Рак": {
        "dates": [(6, 21), (7, 22)],
        "stereotype": "эмоциональный и обидчивый, привязан к дому и семье. "
                      "Заботливый до навязчивости, часто вспоминает прошлое."
    },
    "Лев": {
        "dates": [(7, 23), (8, 22)],
        "stereotype": "королевская особа, жаждет внимания и восхищения. "
                      "Гордый, драматичный, щедрый, но эгоцентричный."
    },
    "Дева": {
        "dates": [(8, 23), (9, 22)],
        "stereotype": "педантичный перфекционист, критикует всё и всех (особенно себя). "
                      "Организованный, практичный, помешан на деталях."
    },
    "Весы": {
        "dates": [(9, 23), (10, 22)],
        "stereotype": "не может принять решение даже под угрозой смерти. "
                      "Любит гармонию, красоту, справедливость и флирт."
    },
    "Скорпион": {
        "dates": [(10, 23), (11, 21)],
        "stereotype": "интенсивный и загадочный, помнит обиды вечно. "
                      "Страстный, ревнивый, проницательный, любит тайны."
    },
    "Стрелец": {
        "dates": [(11, 22), (12, 21)],
        "stereotype": "вечный оптимист-путешественник, говорит правду даже когда не просят. "
                      "Философ, любит свободу и приключения."
    },
    "Козерог": {
        "dates": [(12, 22), (1, 19)],
        "stereotype": "трудоголик с амбициями, серьёзный не по годам. "
                      "Дисциплинированный, ответственный, иногда зануда."
    },
    "Водолей": {
        "dates": [(1, 20), (2, 18)],
        "stereotype": "эксцентричный бунтарь, считает себя умнее всех. "
                      "Независимый, оригинальный, отстранённый эмоционально."
    },
    "Рыбы": {
        "dates": [(2, 19), (3, 20)],
        "stereotype": "мечтатель, живущий в своём мире фантазий. "
                      "Сочувствующий, интуитивный, склонен к эскапизму."
    },
}


def get_zodiac_sign(day: int, month: int) -> str:
    for sign, data in ZODIAC_SIGNS.items():
        start_month, start_day = data["dates"][0]
        end_month, end_day = data["dates"][1]

        if start_month == end_month:
            if month == start_month and start_day <= day <= end_day:
                return sign
        else:
            if (month == start_month and day >= start_day) or \
               (month == end_month and day <= end_day):
                return sign

    return "Неизвестный знак"


def parse_birth_date(text: str) -> Optional[tuple[int, int, int]]:
    for sep in [".", "/", "-"]:
        if sep in text:
            parts = text.strip().split(sep)
            if len(parts) == 3:
                try:
                    day = int(parts[0])
                    month = int(parts[1])
                    year = int(parts[2])
                    datetime(year, month, day)
                    return day, month, year
                except (ValueError, IndexError):
                    continue

    return None


class UserState(StatesGroup):
    waiting_for_birthdate = State()
    asking_question = State()


user_data: dict[int, dict] = {}


# ============== Ollama API Client ==============
async def ask_magic_ball(question: str, zodiac_sign: str, stereotype: str) -> str:
    system_prompt = f"""Ты — мистический магический шар, который предсказывает будущее и отвечает на вопросы.
Ты общаешься с человеком, который по знаку зодиака {zodiac_sign}.
Стереотипные черты этого знака: {stereotype}

Твой ответ должен быть загадочным и мистическим, как настоящее предсказание.
Учитывай стереотипные черты знака зодиака собеседника.
Иногда мягко подшучивай над типичными чертами этого знака.
Ответ на русском языке, кратко (2-4 предложения).
Отвечай как древний оракул, но с юмором."""

    try:
        client = Client(
            host=OLLAMA_HOST,
            headers={'Authorization': f'Bearer {OLLAMA_API_KEY}'}
        )

        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': question},
        ]

        response = await asyncio.to_thread(
            client.chat,
            model='gpt-oss:20b-cloud',
            messages=messages,
            stream=False
        )

        return response['message']['content']

    except Exception as e:
        logger.error(f"Error calling Ollama API: {e}")
        return "🔮 Связь с космосом прервалась... Попробуй ещё раз."


router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id in user_data and "zodiac" in user_data[user_id]:
        zodiac = user_data[user_id]["zodiac"]
        await message.answer(
            f"🔮 С возвращением, о {zodiac}!\n\n"
            f"Задавай свои вопросы магическому шару, и я отвечу тебе.\n"
            f"Используй /reset чтобы ввести новую дату рождения."
        )
        await state.set_state(UserState.asking_question)
    else:
        await message.answer(
            "🔮 *Добро пожаловать к Магическому Шару!*\n\n"
            "Я — древний оракул, который знает ответы на все вопросы.\n"
            "Но сначала мне нужно узнать твою судьбу по звёздам.\n\n"
            "📅 Введи свою дату рождения в формате: *ДД.ММ.ГГГГ*\n"
            "Например: `25.12.1990`",
            parse_mode="Markdown"
        )
        await state.set_state(UserState.waiting_for_birthdate)


@router.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id in user_data:
        del user_data[user_id]

    await message.answer(
        "🔄 Данные сброшены!\n\n"
        "📅 Введи свою дату рождения в формате: *ДД.ММ.ГГГГ*",
        parse_mode="Markdown"
    )
    await state.set_state(UserState.waiting_for_birthdate)


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🔮 *Магический Шар — Справка*\n\n"
        "*Команды:*\n"
        "/start — Начать диалог\n"
        "/reset — Ввести новую дату рождения\n"
        "/zodiac — Узнать свой знак зодиака\n"
        "/help — Эта справка\n\n"
        "*Как пользоваться:*\n"
        "1. Введи дату рождения\n"
        "2. Задавай любые вопросы магическому шару\n"
        "3. Получай предсказания с учётом твоего знака зодиака! ✨",
        parse_mode="Markdown"
    )


@router.message(Command("zodiac"))
async def cmd_zodiac(message: Message):
    user_id = message.from_user.id

    if user_id in user_data and "zodiac" in user_data[user_id]:
        zodiac = user_data[user_id]["zodiac"]
        stereotype = ZODIAC_SIGNS[zodiac]["stereotype"]
        await message.answer(
            f"♈ Твой знак зодиака: *{zodiac}*\n\n"
            f"_{stereotype}_",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "❓ Я ещё не знаю твой знак зодиака.\n"
            "Используй /start чтобы ввести дату рождения."
        )


@router.message(StateFilter(UserState.waiting_for_birthdate))
async def process_birthdate(message: Message, state: FSMContext):
    parsed = parse_birth_date(message.text)

    if parsed is None:
        await message.answer(
            "❌ Не могу распознать дату.\n\n"
            "Пожалуйста, введи дату в формате *ДД.ММ.ГГГГ*\n"
            "Например: `25.12.1990`",
            parse_mode="Markdown"
        )
        return

    day, month, year = parsed
    zodiac_sign = get_zodiac_sign(day, month)

    user_id = message.from_user.id
    user_data[user_id] = {
        "birthdate": (day, month, year),
        "zodiac": zodiac_sign
    }

    stereotype = ZODIAC_SIGNS[zodiac_sign]["stereotype"]

    await message.answer(
        f"✨ *Звёзды говорят:* удача сегодня на твоей стороне, задавай вопрос, искатель знаний!",
        parse_mode="Markdown"
    )
    await state.set_state(UserState.asking_question)


@router.message(StateFilter(UserState.asking_question))
async def process_question(message: Message):
    user_id = message.from_user.id

    if user_id not in user_data or "zodiac" not in user_data[user_id]:
        await message.answer(
            "❓ Я потерял связь с твоими звёздами...\n"
            "Используй /start чтобы начать заново."
        )
        return

    zodiac = user_data[user_id]["zodiac"]
    stereotype = ZODIAC_SIGNS[zodiac]["stereotype"]

    thinking_msg = await message.answer("🔮 *Магический шар сосредоточен...*", parse_mode="Markdown")

    answer = await ask_magic_ball(message.text, zodiac, stereotype)

    save_conversation(user_id, zodiac, message.text, answer)

    await thinking_msg.delete()
    await message.answer(f"🔮 *Магический шар говорит:*\n\n{answer}", parse_mode="Markdown")


@router.message()
async def fallback_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state is None:
        await message.answer(
            "🔮 Привет! Используй /start чтобы начать общение с магическим шаром."
        )


async def main():
    init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(router)

    logger.info("🔮 Магический шар запускается...")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

