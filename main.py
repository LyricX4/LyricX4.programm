import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

class OrderForm(StatesGroup):
    description = State()
    design_style = State()
    username = State()


def get_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💻 Заказать сайт", callback_data="start_order")],
            [
                InlineKeyboardButton(text="📸 Instagram", url="https://www.instagram.com/programmistik0/"),
                InlineKeyboardButton(text="🎥 TikTok", url="https://www.tiktok.com/@lyricx4programm"),
            ],
        ]
    )


def get_cancel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Отменить заказ", callback_data="cancel_order")]]
    )


def get_safe_username(user):
    return f"@{user.username}" if user and user.username else "не указан"


def get_safe_contact(message: Message, entered_text: str | None = None) -> str:
    if entered_text and entered_text.strip() and entered_text.strip() != "+":
        return entered_text.strip()
    username = get_safe_username(message.from_user)
    return username if username != "не указан" else "не указан"

async def main():
    token = os.getenv("BOT_TOKEN")
    admin_id_value = os.getenv("ADMIN_ID")

    if not token:
        raise RuntimeError("Не задан BOT_TOKEN. Установи переменную окружения с токеном от @BotFather.")
    if not admin_id_value:
        raise RuntimeError("Не задан ADMIN_ID. Установи переменную окружения со своим Telegram ID.")
    try:
        admin_id = int(admin_id_value)
    except ValueError as e:
        raise RuntimeError("ADMIN_ID должен быть числом.") from e

    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())

    # --- Отмена заказа ---
    @dp.callback_query(F.data == "cancel_order")
    async def cancel_handler(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.answer("Заказ отменен.", reply_markup=get_main_keyboard())
        await callback.answer()

    # --- Старт ---
    @dp.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext):
        await state.clear()
        text = (
            "👋 **Привет! Я бот для заказа сайтов.**\n\n"
            "Здесь ты можешь оформить заявку на разработку стильного веб-сайта "
            "или перейти в мои социальные сети."
        )
        await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

    # --- Начало оформления заказа ---
    @dp.callback_query(F.data == "start_order")
    async def start_order(callback: CallbackQuery, state: FSMContext):
        await state.set_state(OrderForm.description)
        await callback.message.answer(
            "📋 **Шаг 1 из 3:**\n\n"
            "Опиши максимально подробно, какой сайт тебе нужен:\n"
            "• Тип (лендинг, портфолио, интернет-магазин)\n"
            "• Что должно быть на сайте (секции, кнопки, формы)\n"
            "• Основная цель сайта",
            reply_markup=get_cancel_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer()

    # --- Шаг 1: Описание ---
    @dp.message(OrderForm.description)
    async def process_description(message: Message, state: FSMContext):
        await state.update_data(description=message.text)
        await state.set_state(OrderForm.design_style)
        await message.answer(
            "🎨 **Шаг 2 из 3:**\n\n"
            "Укажи пожелания по дизайну и стилю:\n"
            "• Цвета (например: темно-фиолетовый градиент, неоновые акценты)\n"
            "• Ссылки на примеры сайтов, которые тебе нравятся",
            reply_markup=get_cancel_keyboard(),
            parse_mode="Markdown"
        )

    # --- Шаг 2: Дизайн ---
    @dp.message(OrderForm.design_style)
    async def process_design(message: Message, state: FSMContext):
        await state.update_data(design_style=message.text)
        await state.set_state(OrderForm.username)
        
        # Получаем юзернейм клиента, если он есть
        user_tg = f"@{message.from_user.username}" if message.from_user.username else "Не указан в профиле"
        
        await message.answer(
            f"📞 **Шаг 3 из 3:**\n\n"
            f"Укажи свой контакт для связи (Telegram юзернейм или номер телефона).\n"
            f"По умолчанию: {user_tg}\n\n"
            f"Напиши свой юзернейм или отправь **«+»**, чтобы использовать юзернейм профиля.",
            reply_markup=get_cancel_keyboard(),
            parse_mode="Markdown"
        )

    # --- Шаг 3: Контакт и отправка администратору ---
    @dp.message(OrderForm.username)
    async def process_username(message: Message, state: FSMContext):
        contact = get_safe_contact(message, message.text)
        if message.text and message.text.strip() == "+":
            contact = get_safe_username(message.from_user)

        data = await state.get_data()
        await state.clear()

        await message.answer(
            "✅ **Спасибо! Твой заказ отправлен.**\n"
            "Я свяжусь с тобой в ближайшее время для уточнения деталей.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )

        safe_username = get_safe_username(message.from_user)
        admin_text = (
            "🚀 **НОВЫЙ ЗАКАЗ НА САЙТ!**\n\n"
            f"👤 **Заказчик:** {message.from_user.full_name} ({safe_username})\n"
            f"📞 **Контакт для связи:** {contact}\n"
            f"🆔 **ID заказчика:** `{message.from_user.id}`\n\n"
            f"📝 **Описание сайта:**\n{data.get('description', 'Не указано')}\n\n"
            f"🎨 **Стиль и дизайн:**\n{data.get('design_style', 'Не указано')}"
        )

        try:
            await bot.send_message(chat_id=admin_id, text=admin_text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Не удалось отправить заказ админу: {e}")

    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
