import asyncio
import os
import tempfile
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

from documents import load_pdf

load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Привет! Пришли PDF с лекцией.")


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
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, name)
        await bot.download(doc, destination=path)
        try:
            pages = await asyncio.to_thread(load_pdf, path)
        except Exception:
            logging.exception("Не удалось прочитать PDF")
            await message.answer("Не смог прочитать файл.")
            return
    await message.answer(f"Готово: {len(pages)} стр. с текстом.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
