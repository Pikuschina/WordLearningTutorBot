import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InputFile
from aiogram.enums import ParseMode
from aiogram.utils.markdown import bold
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import aiosqlite

API_TOKEN = '7328028910:AAGwoLI7hQawY22BqxBdD7np2a8cD915J5g'  # ← замени на свой токен

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

DB_PATH = 'words.db'
IMAGE_FOLDER = 'images'

# Убедимся, что папка для картинок существует
os.makedirs(IMAGE_FOLDER, exist_ok=True)

REVIEW_DAYS = [0, 1, 3, 9, 21, 25]

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS words (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                file_path TEXT,
                upload_date TEXT
            )
        ''')
        await db.commit()

@dp.message()
async def handle_image(message: types.Message):
    if not message.photo:
        await message.reply("Пожалуйста, отправь картинку.")
        return

    file_id = message.photo[-1].file_id
    file = await bot.get_file(file_id)
    file_path = f"{IMAGE_FOLDER}/{file_id}.jpg"
    await bot.download_file(file.file_path, file_path)

    # Сохраняем картинку в БД
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO words (user_id, file_path, upload_date) VALUES (?, ?, ?)",
            (message.from_user.id, file_path, datetime.now().isoformat())
        )
        await db.commit()

    await message.reply("Картинка сохранена и будет показана по расписанию 0-1-3-9-21-25.")

async def send_reminders():
    today = datetime.now().date()

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, file_path, upload_date FROM words") as cursor:
            rows = await cursor.fetchall()
            for user_id, file_path, upload_date in rows:
                upload_dt = datetime.fromisoformat(upload_date).date()
                days_passed = (today - upload_dt).days
                if days_passed in REVIEW_DAYS:
                    try:
                        await bot.send_photo(user_id, InputFile(file_path),
                            caption=f"Повторение {bold(f'День {days_passed}')} для этого слова.",
                            parse_mode=ParseMode.MARKDOWN)
                    except Exception as e:
                        logging.error(f"Не удалось отправить картинку: {e}")

async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    scheduler.add_job(send_reminders, "cron", hour=9)  # отправка в 09:00 каждый день
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())