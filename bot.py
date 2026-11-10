import asyncio
import json
import os
import logging

from config import TG_MESSAGE_LIMIT, MAX_FILE_MB, BOT_TOKEN, TOP_K, MIN_SCORE
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, BotCommand, ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from documents import load_pdf, chunk_pages, count_pages, skipped_pages, file_hash
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


def upload_message(pages: list[dict], total: int) -> str:
    """Итог загрузки: сколько страниц прочитано и какие пропущены."""
    skipped = skipped_pages(pages, total)
    if not skipped:
        return f"Загружено: {total} {pages_word(total)}"
    shown = ", ".join(map(str, skipped[:20]))
    if len(skipped) > 20:
        shown += f" и ещё {len(skipped) - 20}"
    return (
        f"Загружено страниц: {len(pages)} из {total}.\n"
        f"Без текста (скан или картинка), пропущены: стр. {shown}"
    )


def pages_word(n: int) -> str:
    """Склоняет слово «страница» под число: 1 страница, 3 страницы, 5 страниц."""
    if n % 10 == 1 and n % 100 != 11:
        return "страница"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return "страницы"
    return "страниц"

BTN_SUMMARY = "📄 Выжимка"
BTN_CARDS = "🃏 Карточки"
BTN_CHEATSHEET = "📝 Шпаргалка"
BTN_DOCS = "📚 Мои лекции"
BTN_DELETE = "🗑 Удалить лекцию"

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=BTN_SUMMARY),
            KeyboardButton(text=BTN_CARDS),
            KeyboardButton(text=BTN_CHEATSHEET),
        ],
        [KeyboardButton(text=BTN_DOCS), KeyboardButton(text=BTN_DELETE)],
    ],
    resize_keyboard=True,
)


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Привет! Пришли PDF с лекцией.", reply_markup=MAIN_KEYBOARD
    )


DATA_DIR = "data"


def find_same_file(path: str, docs: list[dict]) -> dict | None:
    """Ищет среди документов пользователя файл с тем же содержимым."""
    new_hash = file_hash(path)
    for d in docs:
        if os.path.exists(d["path"]) and file_hash(d["path"]) == new_hash:
            return d
    return None


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
    same = await asyncio.to_thread(find_same_file, path, docs)
    if same is not None:
        os.remove(path)
        await message.answer(f"Эта лекция уже загружена как «{same['filename']}».")
        return
    try:
        pages = await asyncio.to_thread(load_pdf, path)
        total = await asyncio.to_thread(count_pages, path)
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
    await message.answer(upload_message(pages, total))


# Что делаем в каждом режиме: название для сообщения «Делаю ...»
LABELS = {"summary": "выжимку", "cards": "карточки", "cheatsheet": "шпаргалку"}


def parse_cards(raw: str) -> list[dict]:
    """JSON с карточками -> список {"question": ..., "answer": ...}."""
    cards = json.loads(raw)
    if not isinstance(cards, list) or not cards:
        raise ValueError("Карточек нет")
    return [{"question": str(c["question"]), "answer": str(c["answer"])} for c in cards]


def card_view(cards: list[dict], doc_id: int, i: int, show: bool):
    """Текст и кнопки одной карточки. В callback_data: card:<номер>:<ответ>:<doc_id>."""
    card = cards[i]
    text = f"Карточка {i + 1} из {len(cards)}\n\n❓ {card['question']}"
    builder = InlineKeyboardBuilder()
    rows = []
    if show:
        text += f"\n\n💡 {card['answer']}"
    else:
        builder.button(text="Показать ответ", callback_data=f"card:{i}:1:{doc_id}")
        rows.append(1)
    nav = 0
    if i > 0:
        builder.button(text="◀ Назад", callback_data=f"card:{i - 1}:0:{doc_id}")
        nav += 1
    if i + 1 < len(cards):
        builder.button(text="Дальше ▶", callback_data=f"card:{i + 1}:0:{doc_id}")
        nav += 1
    if nav:
        rows.append(nav)
    builder.adjust(*rows)
    return text, builder.as_markup()


NO_CREDITS_TEXT = "У бота закончился лимит модели, напиши админу."


async def send_result(message: Message, kind: str) -> None:
    """/summary, /cards, /cheatsheet: если лекций несколько, спрашиваем какую."""
    docs = await asyncio.to_thread(db.list_documents, message.from_user.id)
    if not docs:
        await message.answer("Сначала пришли PDF с лекцией.")
        return
    if len(docs) == 1:
        await make_result(message, kind, docs[0])
        return
    builder = InlineKeyboardBuilder()
    for d in docs:
        builder.button(text=d["filename"], callback_data=f"res:{kind}:{d['doc_id']}")
    builder.adjust(1)
    await message.answer(
        f"По какой лекции сделать {LABELS[kind]}?", reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data.startswith("res:"))
async def choose_document(callback: CallbackQuery):
    """Выбрали лекцию кнопкой: убираем кнопки и делаем результат."""
    kind = callback.data.split(":")[1]
    doc = await get_own_document(callback)
    if doc is None or kind not in LABELS:
        await callback.message.edit_text("Лекция не найдена.")
        await callback.answer()
        return
    await callback.message.edit_text(f"Лекция: {doc['filename']}")
    await callback.answer()
    await make_result(callback.message, kind, doc)


async def make_result(message: Message, kind: str, doc: dict) -> None:
    """Достаёт результат из кэша или просит модель, затем отправляет."""
    label = LABELS[kind]
    text = await asyncio.to_thread(db.get_cached, doc["doc_id"], kind)
    if text is None:
        await message.answer(
            f"Делаю {label} «{doc['filename']}»... "
            "Для длинной лекции это может занять несколько минут."
        )
        try:
            pages = await asyncio.to_thread(load_pdf, doc["path"])
            chunks = chunk_pages(pages)
            text = await asyncio.to_thread(llm.ask, "", chunks, kind)
            if kind == "cards":
                parse_cards(text)  # проверяем формат до записи в кэш
        except llm.LLMBusyError:
            await message.answer("Модель сейчас перегружена, попробуй через минуту.")
            return
        except llm.LLMNoCreditsError:
            await message.answer(NO_CREDITS_TEXT)
            return
        except Exception:
            logging.exception("Не удалось сделать %s", kind)
            await message.answer(f"Не получилось сделать {label}, попробуй позже.")
            return
        await asyncio.to_thread(db.save_cached, doc["doc_id"], kind, text)
    if kind == "cards":
        card_text, markup = card_view(parse_cards(text), doc["doc_id"], 0, False)
        await message.answer(card_text, reply_markup=markup)
        return
    for part in split_message(text):
        await message.answer(part)


@dp.callback_query(F.data.startswith("card:"))
async def flip_card(callback: CallbackQuery):
    """Показать ответ или перейти к другой карточке (то же сообщение)."""
    _, i, show, _ = callback.data.split(":")
    doc = await get_own_document(callback)
    raw = None
    if doc is not None:
        raw = await asyncio.to_thread(db.get_cached, doc["doc_id"], "cards")
    if raw is None:
        await callback.message.edit_text("Карточки не найдены, нажми «Карточки» ещё раз.")
        await callback.answer()
        return
    cards = parse_cards(raw)
    i = int(i)
    if not 0 <= i < len(cards):
        await callback.answer()
        return
    text, markup = card_view(cards, doc["doc_id"], i, show == "1")
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@dp.message(Command("summary"))
@dp.message(F.text == BTN_SUMMARY)
async def summary(message: Message):
    await send_result(message, "summary")


@dp.message(Command("cards"))
@dp.message(F.text == BTN_CARDS)
async def cards(message: Message):
    await send_result(message, "cards")


@dp.message(Command("cheatsheet"))
@dp.message(F.text == BTN_CHEATSHEET)
async def cheatsheet(message: Message):
    await send_result(message, "cheatsheet")


@dp.message(Command("docs"))
@dp.message(F.text == BTN_DOCS)
async def show_docs(message: Message):
    """Список загруженных лекций пользователя."""
    docs = await asyncio.to_thread(db.list_documents, message.from_user.id)
    if not docs:
        await message.answer("Загруженных лекций нет")
        return
    lines = [f"{i}. {d['filename']}" for i, d in enumerate(docs, start=1)]
    await message.answer("Твои лекции:\n" + "\n".join(lines))


def delete_list_keyboard(docs: list[dict]):
    """Кнопка на каждый документ, в callback_data только doc_id."""
    builder = InlineKeyboardBuilder()
    for d in docs:
        builder.button(text=f"🗑 {d['filename']}", callback_data=f"del:{d['doc_id']}")
    builder.adjust(1)
    return builder.as_markup()


@dp.message(Command("delete"))
@dp.message(F.text == BTN_DELETE)
async def delete_menu(message: Message):
    """Показывает список лекций для удаления."""
    docs = await asyncio.to_thread(db.list_documents, message.from_user.id)
    if not docs:
        await message.answer("Загруженных лекций нет")
        return
    await message.answer(
        "Какую лекцию удалить?", reply_markup=delete_list_keyboard(docs)
    )

async def get_own_document(callback: CallbackQuery) -> dict | None:
    """Достаёт doc_id из callback_data и проверяет, что документ свой."""
    doc_id = int(callback.data.split(":")[-1])
    doc = await asyncio.to_thread(db.get_document, doc_id)
    if doc is None or doc["user_id"] != callback.from_user.id:
        return None
    return doc


@dp.callback_query(F.data.startswith("del:"))
async def ask_confirm(callback: CallbackQuery):
    """Нажали на документ: спрашиваем подтверждение."""
    doc = await get_own_document(callback)
    if doc is None:
        await callback.message.edit_text("Лекция не найдена.")
        await callback.answer()
        return
    builder = InlineKeyboardBuilder()
    builder.button(text="Да", callback_data=f"yes:{doc['doc_id']}")
    builder.button(text="Отмена", callback_data="cancel")
    await callback.message.edit_text(
        f"Удалить {doc['filename']}?", reply_markup=builder.as_markup()
    )
    await callback.answer()


@dp.callback_query(F.data == "cancel")
async def cancel_delete(callback: CallbackQuery):
    """Отмена: возвращаем список лекций."""
    docs = await asyncio.to_thread(db.list_documents, callback.from_user.id)
    if docs:
        await callback.message.edit_text(
            "Какую лекцию удалить?", reply_markup=delete_list_keyboard(docs)
        )
    else:
        await callback.message.edit_text("Загруженных лекций нет")
    await callback.answer()


@dp.callback_query(F.data.startswith("yes:"))
async def confirm_delete(callback: CallbackQuery):
    """Подтвердили: удаляем куски в Chroma, запись в базе и PDF."""
    doc = await get_own_document(callback)
    if doc is None:
        await callback.message.edit_text("Лекция не найдена.")
        await callback.answer()
        return
    try:
        await asyncio.to_thread(
            search.delete_document, callback.from_user.id, doc["doc_id"]
        )
        await asyncio.to_thread(db.delete_document, doc["doc_id"])
    except Exception:
        logging.exception("Не удалось удалить документ")
        await callback.message.edit_text("Не получилось удалить, попробуй позже.")
        await callback.answer()
        return
    if os.path.exists(doc["path"]):
        await asyncio.to_thread(os.remove, doc["path"])
    await callback.message.edit_text(f"Удалено: {doc['filename']}")
    await callback.answer()


@dp.message(F.text & ~F.text.startswith("/"))
async def answer_question(message: Message):
    question = message.text.strip()
    user_id = message.from_user.id
    chunks = await asyncio.to_thread(search.search, question, user_id, TOP_K)
    if not chunks:
        await message.answer("Сначала пришли PDF с лекцией.")
        return
    good = [c for c in chunks if c["score"] >= MIN_SCORE]
    if not good:
        await message.answer("В материалах ответа не нашёл.")
        return
    try:
        answer = await asyncio.to_thread(llm.ask, question, good, "answer")
    except llm.LLMBusyError:
        await message.answer("Модель сейчас перегружена, попробуй через минуту.")
        return
    except llm.LLMNoCreditsError:
        await message.answer(NO_CREDITS_TEXT)
        return
    except Exception:
        logging.exception("Не удалось ответить на вопрос")
        await message.answer("Не получилось ответить, попробуй позже.")
        return
    if answer.strip().rstrip(".") != "В материалах ответа не нашёл":
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
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать и показать меню"),
        BotCommand(command="summary", description="Выжимка лекции"),
        BotCommand(command="cards", description="Карточки для заучивания"),
        BotCommand(command="cheatsheet", description="Шпаргалка"),
        BotCommand(command="docs", description="Мои лекции"),
        BotCommand(command="delete", description="Удалить лекцию"),
    ])
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
