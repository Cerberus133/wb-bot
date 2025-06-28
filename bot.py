import asyncio
import sqlite3
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- НАСТРОЙКИ ---
API_TOKEN = os.getenv('API_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
CHANNELS = ['@DartalOmsk', '@DartalSamara', '@DartalChelyabinsk', '@DartalEKB', '@DartalTymen']


# --- ИНИЦИАЛИЗАЦИЯ БОТА ---
bot = Bot(token=API_TOKEN, parse_mode=types.ParseMode.HTML) # Добавим parse_mode по умолчанию
dp = Dispatcher(bot)


# --- РАБОТА С БАЗОЙ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_seen TEXT NOT NULL
    )''')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone() is None:
        current_date = datetime.now().isoformat()
        cursor.execute("INSERT INTO users (user_id, first_seen) VALUES (?, ?)", (user_id, current_date))
        conn.commit()
    conn.close()


# --- ФУНКЦИЯ ПРОВЕРКИ ПОДПИСКИ ---
async def check_subscription(user_id):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except Exception:
            return False
    return True


# --- ШАГ 1: Начало диалога по команде /start ---
@dp.message_handler(commands=['start'])
async def command_start(message: types.Message):
    add_user(message.from_user.id)
    if await check_subscription(message.from_user.id):
        await send_main_script(message)
    else:
        # Создаем Reply-кнопку
        start_kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="✅ГОТОВ✅")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer(
            """Привет! Ты попал туда, где реально подключить настоящий Mystery Pack от WB  👋 \n\nЭто интерактивный "подарочный" формат, в котором ты получаешь шанс открыть 1 пакет в день.
Из него выпадут три одинаковые карточки, но выбрать можно только одну. Один день — одна попытка.\n\n🎁 Что в призах?\n\n Абсолютная случайность: может попасться что-то стоящее, а может — пусто. 🎯\n\n Здесь всё зависит от удачи и чуть-чуть везения \n \n \nГотов попробовать?""",
            reply_markup=start_kb
        )


# --- ШАГ 2: Пользователь нажимает Reply-кнопку "✅ГОТОВ✅" ---
@dp.message_handler(lambda message: message.text == "✅ГОТОВ✅")
async def show_choice_menu(message: types.Message):
    choice_keyboard = InlineKeyboardMarkup(row_width=1)
    choice_keyboard.add(
        InlineKeyboardButton(text="📱ТЕХНИКА📱", callback_data="show_channels_list"),
        InlineKeyboardButton(text="🖤КОСМЕТИКА🖤", callback_data="show_channels_list"),
        InlineKeyboardButton(text="💍УКРАШЕНИЯ💍", callback_data="show_channels_list")
    )
    await message.answer(
        "Подскажи, какое содержимое MYSTERY ПАК ты бы хотел видеть больше всего?\n\n"
        "Выбери интересующую тебя категорию:",
        reply_markup=choice_keyboard
    )


# --- ШАГ 3: Пользователь нажимает на одну из трех инлайн-кнопок ---
@dp.callback_query_handler(text="show_channels_list")
async def process_choice_and_show_channels(callback_query: types.CallbackQuery):
    channels_keyboard = InlineKeyboardMarkup(row_width=1)
    for channel_username in CHANNELS:
        link = f"https://t.me/{channel_username[1:]}"
        channels_keyboard.add(InlineKeyboardButton(text=f"Подписаться на {channel_username}", url=link))
    channels_keyboard.add(InlineKeyboardButton(text="♻️ Проверить подписку", callback_data="check_sub"))

    # Используем тройные кавычки для чистого текста
    text = """Отлично, постараемся выбрать для вас наиболее подходящее содержимое

Остались последние действия, чтобы получить MYSTERY ПАК.
Эта акция проводится благодаря Нашим Спонсорам.

ДЛЯ ПОЛУЧЕНИЯ MYSTERY ПАКа вам необходимо подписаться на наших спонсоров

Чтобы Каналы не мешали, отключите в них уведомления и переместите в Архив."""

    await callback_query.message.edit_text(text, reply_markup=channels_keyboard)
    await callback_query.answer()


# --- ШАГ 4: Пользователь нажимает "Проверить подписку" ---
@dp.callback_query_handler(text="check_sub")
async def check_sub_callback(callback_query: types.CallbackQuery):
    if await check_subscription(callback_query.from_user.id):
        await callback_query.message.delete()
        await send_main_script(callback_query.message)
    else:
        await callback_query.answer(
            "Подписка не найдена. Пожалуйста, подпишитесь и попробуйте снова.",
            show_alert=True
        )


# --- АДМИН-ПАНЕЛЬ ---
@dp.message_handler(commands=['stats'])
async def get_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(user_id) FROM users")
    total_users = cursor.fetchone()[0]
    current_month = datetime.now().strftime('%Y-%m')
    cursor.execute("SELECT COUNT(user_id) FROM users WHERE strftime('%Y-%m', first_seen) = ?", (current_month,))
    month_users = cursor.fetchone()[0]
    current_day = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT COUNT(user_id) FROM users WHERE strftime('%Y-%m-%d', first_seen) = ?", (current_day,))
    today_users = cursor.fetchone()[0]
    conn.close()

    await message.answer(
        f"📊 <b>Статистика бота:</b>\n\n"
        f"👤 <b>Всего пользователей:</b> {total_users}\n"
        f"🗓 <b>Новых за этот месяц:</b> {month_users}\n"
        f"☀️ <b>Новых за сегодня:</b> {today_users}"
    )


# --- ОСНОВНОЙ СКРИПТ (КОНТЕНТ) ПОСЛЕ ПОДПИСКИ ---
async def send_main_script(message: types.Message):
    await message.answer("🐙Спасибо за подписку!🐙", reply_markup=types.ReplyKeyboardRemove())
    await asyncio.sleep(1)
    await message.answer("Ожидайте ссылку на скачивание в порядке очереди")
    await asyncio.sleep(1)
    await message.answer("Обычно это занимает от 24 до 72 часов.\nВ редких случаях бывают задержки")
    await asyncio.sleep(1)
    await message.answer("Спасибо за понимание☺️")


# --- ЗАПУСК БОТА ---
if __name__ == '__main__':
    init_db()
    executor.start_polling(dp, skip_updates=True)