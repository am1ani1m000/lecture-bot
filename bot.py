import asyncio
import os
import logging

from config import TG_MESSAGE_LIMIT
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

from documents import load_pdf
import db

import llm



load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

def split_message(text: str, limit: int = TG_MESSAGE_LIMIT) -> list[str]:
    """Режет длинный текст на части по границам абзацев."""
    parts, current = [], ""
    for para in text.split("\n\n"):
        while len(para) > limit:
            if current:
                parts.append(current)
                current = ""
            parts.append(para[:limit])
            para = para[limit:]
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= limit:
            current = candidate
        else:
            parts.append(current)
            current = para
    if current:
        parts.append(current)
    return parts

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


@dp.message(Command("summary"))
async def summary(message: Message):
    docs = await asyncio.to_thread(db.list_documents, message.from_user.id)
    if not docs:
        await message.answer("Сначала пришли PDF с лекцией.")
        return
    doc = docs[0]
    text = await asyncio.to_thread(db.get_cached, doc["doc_id"], "summary")
    if text is None:
        await message.answer(f"Делаю выжимку «{doc['filename']}»...")
        try:
            pages = await asyncio.to_thread(load_pdf, doc["path"])
            text = await asyncio.to_thread(llm.ask, "", pages, "summary")
        except llm.LLMBusyError:
            await message.answer("Модель сейчас перегружена, попробуй через минуту.")
            return
        except Exception:
            logging.exception("Не удалось сделать выжимку")
            await message.answer("Не получилось сделать выжимку, попробуй позже.")
            return
        await asyncio.to_thread(db.save_cached, doc["doc_id"], "summary", text)
    for part in split_message(text):
        await message.answer(part)

    
async def main():
    db.init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
