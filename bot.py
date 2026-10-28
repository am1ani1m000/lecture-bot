import asyncio
import os
import logging

from config import TG_MESSAGE_LIMIT, MAX_FILE_MB, BOT_TOKEN, TOP_K, MIN_SCORE
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from documents import load_pdf, chunk_pages
import db
import search 
import llm



bot = Bot(token=BOT_TOKEN)
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
    if doc.file_size and doc.file_size > MAX_FILE_MB * 1024 * 1024:
        await message.answer(f"Файл больше {MAX_FILE_MB} МБ, такой я не скачаю.")
        return
    user_id = message.from_user.id
    docs = await asyncio.to_thread(db.list_documents, user_id)
    if any(d["filename"] == name for d in docs):
        await message.answer(f"Лекция «{name}» уже загружена.")
        return
    await message.answer("Читаю файл...")
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
    chunks = chunk_pages(pages)
    doc_id = None
    try:
        doc_id = await asyncio.to_thread(
            db.add_document, user_id, name, path, len(pages), len(chunks)
        )
        await asyncio.to_thread(search.add_chunks, chunks, user_id, doc_id)
    except Exception:
        logging.exception("Не удалось сохранить документ")
        if doc_id is not None:
            await asyncio.to_thread(db.delete_document, doc_id)
        os.remove(path)
        await message.answer("Не смог сохранить лекцию, попробуй позже.")
        return
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
            chunks = chunk_pages(pages)
            text = await asyncio.to_thread(llm.ask, "", chunks, "summary")
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

@dp.message(F.text & ~F.text.startswith("/"))
async def answer_question(message: Message):
    question = message.text.strip()
    user_id = message.from_user.id
    chunks = await asyncio.to_thread(search.search, question, user_id, TOP_K)
    if not chunks:
        await message.answer("Сначала пришли PDF с лекцией.")
        return
    if chunks[0]["score"] < MIN_SCORE:
        await message.answer("В материалах ответа не нашёл.")
        return
    try:
        answer = await asyncio.to_thread(llm.ask, question, chunks, "answer")
    except llm.LLMBusyError:
        await message.answer("Модель сейчас перегружена, попробуй через минуту.")
        return
    except Exception:
        logging.exception("Не удалось ответить на вопрос")
        await message.answer("Не получилось ответить, попробуй позже.")
        return
    if "В материалах ответа не нашёл" not in answer:
        good = [c for c in chunks if c["score"] >= MIN_SCORE]
        pages_by_file: dict[str, set[int]] = {}
        for c in good:
            pages_by_file.setdefault(c["source"], set()).add(c["page"])
        refs = [f"{name}, стр. {', '.join(map(str, sorted(pages)))}"
                for name, pages in pages_by_file.items()]
        answer += "\n\nИсточник: " + "; ".join(refs)
    for part in split_message(answer):
        await message.answer(part)

async def main():
    logging.basicConfig(level=logging.INFO)
    db.init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
