import asyncio
import os
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

from documents import load_pdf
import db

load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Привет! Пришли PDF с лекцией.")


DATA_DIR = "data"


@dp.message(F.document)
async def handle_document(message: Message):
    doc = message.document
    name = os.path.basename(doc.file_name or "")
    if not name.lower().endswith(".pdf"):
        await message.answer("Пока я принимаю только PDF.")
        return
    if doc.file_size and doc.file_size > 20 * 1024 * 1024:
        await message.answer("Файл больше 20 МБ, такой я не скачаю.")
        return
    await message.answer("Читаю файл...")
    user_id = message.from_user.id
    folder = os.path.join(DATA_DIR, str(user_id))
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    await bot.download(doc, destination=path)
    try:
        pages = await asyncio.to_thread(load_pdf, path)
    except Exception:
        logging.exception("Не удалось прочитать PDF")
        os.remove(path)
        await message.answer("Не смог прочитать файл.")
        return
    if not pages:
        os.remove(path)
        await message.answer("Текст в файле не найден, пришли PDF с текстом.")
        return
    await asyncio.to_thread(db.add_document, user_id, name, path, len(pages), 0)
    await message.answer(f"Загружено: {len(pages)} страниц")
    
async def main():
    db.init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
