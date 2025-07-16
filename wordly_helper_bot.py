import os
import logging
import random
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# Загрузка .env
load_dotenv(".env")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Загрузка словаря
with open("five_letter_words.txt", encoding="utf-8") as f:
    WORDS = set(line.strip().lower() for line in f if len(line.strip()) == 5)

# Состояние пользователей
user_sessions = {}
feedback_state = {}

# Тексты
START_TEXT = """
👋 Привет!

Я — твой помощник для игры в «5 букв» и любых аналогов Wordly на русском языке.

📝 Что я умею?
Я помогу тебе угадать слово:
• буду предлагать самые частотные слова для начала,
• после каждой твоей попытки — фильтровать список,
• и подсказывать лучшие варианты для следующего хода.

💡 Как пользоваться ботом?
1️⃣ Нажми 🎯 «Начать игру», я предложу слова для старта.
2️⃣ После своей попытки в игре пришли мне результат в виде:
   `0` — буквы нет ⬜
   `1` — буква на месте 🟩
   `2` — буква есть, но не на месте 🟨
Например: `01210`.

👇 Выбери, что хочешь сделать:
"""

HELP_TEXT = """
ℹ️ Помощь

Я — твой помощник для игры в «5 букв» и других аналогов Wordly на русском языке.

Вот что я умею:

🎯 *Начать игру*
— Предложу самые частотные слова для первого хода. 
— Ты можешь выбрать слово кнопкой или написать своё.

🔢 *Ввести результат*
— После того как попробуешь слово в игре, пришли мне код результата:
  • `0` — буквы нет ⬜
  • `1` — буква на месте 🟩
  • `2` — буква есть, но не на месте 🟨
Пример: `02110`.

📝 *История ходов*
— Покажу все твои прошлые попытки в виде цветных строк.

✅ *Слово угадано*
— Поздравлю и предложу начать заново без лишних вводов.

🔙 *Удалить последний ход*
— Уберу последнюю попытку, если ошибся.

♻️ *Начать заново*
— Полностью сброшу твою историю и предложу начать сначала.

✉️ *Обратная связь*
— Хочешь оставить отзыв? Напиши /feedback. Сначала текст, потом оценку от 1 💩 до 5 🚀.
"""

# Универсальная отправка сообщений
async def send_message(update, text, reply_markup=None, parse_mode=None):
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

# Главное меню
def main_menu():
    keyboard = [
        [InlineKeyboardButton("🎯 Начать игру", callback_data="start_game")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help"),
         InlineKeyboardButton("✉️ Обратная связь", callback_data="feedback")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Игровое меню
def game_menu():
    keyboard = [
        [InlineKeyboardButton("🔙 Удалить последний ход", callback_data="undo"),
         InlineKeyboardButton("♻️ Начать заново", callback_data="restart")],
        [InlineKeyboardButton("✅ Слово угадано", callback_data="guessed")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help"),
         InlineKeyboardButton("✉️ Обратная связь", callback_data="feedback")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"DEBUG: start update = {update}")
    user_sessions[update.effective_user.id] = {
        "history": [],
        "possible_words": list(WORDS)
    }
    await send_message(update, START_TEXT, reply_markup=main_menu())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"DEBUG: help update = {update}")
    await send_message(update, HELP_TEXT, reply_markup=main_menu(), parse_mode="Markdown")

# Обратная связь
async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"DEBUG: feedback_start update = {update}")
    feedback_state[update.effective_user.id] = {"step": "await_text"}
    await send_message(update, "✍️ Напиши свой отзыв или предложение. Когда закончишь — просто отправь текст.")

async def feedback_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    print(f"DEBUG: feedback_message update = {update}")
    if feedback_state.get(user_id, {}).get("step") == "await_text":
        feedback_state[user_id]["text"] = update.message.text
        feedback_state[user_id]["step"] = "await_rating"
        keyboard = [
            [InlineKeyboardButton("1 💩", callback_data="rating_1"),
             InlineKeyboardButton("2 😕", callback_data="rating_2"),
             InlineKeyboardButton("3 🙂", callback_data="rating_3"),
             InlineKeyboardButton("4 👍", callback_data="rating_4"),
             InlineKeyboardButton("5 🚀", callback_data="rating_5")]
        ]
        await send_message(update, "Спасибо! Теперь оцени меня:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    print(f"DEBUG: handle_rating update = {update}")
    await query.answer()
    rating = query.data.split("_")[1]
    user_id = query.from_user.id
    feedback_text = feedback_state.get(user_id, {}).get("text", "")
    with open("feedback_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] FEEDBACK: {feedback_text}\nRATING: {rating}\n\n")
    await query.edit_message_text("Спасибо за отзыв и оценку! 🚀")
    feedback_state.pop(user_id, None)

# Кнопки
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    print(f"DEBUG: handle_buttons update = {update}")
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "start_game":
        user_sessions[user_id] = {"history": [], "possible_words": list(WORDS)}
        top_words = random.sample(user_sessions[user_id]["possible_words"], 5)
        buttons = [[InlineKeyboardButton(w.upper(), callback_data=f"word_{w}")] for w in top_words]
        await send_message(update, "🎯 Выбери слово для хода или напиши своё:", 
                           reply_markup=InlineKeyboardMarkup(buttons + list(game_menu().inline_keyboard)))

    elif data.startswith("word_"):
        word = data[5:]
        await process_word_choice(update, context, user_id, word)

    elif data == "undo":
        if user_sessions[user_id]["history"]:
            user_sessions[user_id]["history"].pop()
            await send_message(update, "Удалил последний ход.", reply_markup=game_menu())
        else:
            await send_message(update, "История пустая.", reply_markup=game_menu())

    elif data == "restart":
        await start(update, context)

    elif data == "guessed":
        await query.edit_message_text(
            "🎉 Поздравляю! Ты угадал слово!\n\nХочешь сыграть ещё раз?",
            reply_markup=main_menu()
        )
        user_sessions[user_id] = {
            "history": [],
            "possible_words": list(WORDS)
        }

    elif data == "help":
        await send_message(update, HELP_TEXT, parse_mode="Markdown", reply_markup=main_menu())

    elif data == "feedback":
        await feedback_start(update, context)

# Слова
async def process_word_choice(update, context, user_id, word):
    print(f"DEBUG: process_word_choice word = {word}")
    if word not in WORDS:
        keyboard = [[InlineKeyboardButton("✅ Да, всё правильно", callback_data=f"confirm_{word}"),
                     InlineKeyboardButton("✏️ Исправить", callback_data="start_game")]]
        await send_message(update,
            f"⚠️ Слово {word.upper()} не найдено в словаре. Это точно то слово, которое ты ввёл в игре?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        session = user_sessions[user_id]
        session["history"].append({"word": word, "pattern": None})
        await send_message(update,
            f"Принято слово {word.upper()}.\n"
            "Теперь пришли результат вида 02120, где:\n"
            "0 — буквы нет ⬜\n"
            "1 — буква на месте 🟩\n"
            "2 — буква есть, но не на месте 🟨",
            reply_markup=game_menu()
        )

# Тексты
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"DEBUG: handle_message update = {update}")
    user_id = update.effective_user.id

    if feedback_state.get(user_id, {}).get("step") == "await_text":
        await feedback_message(update, context)
        return

    text = update.message.text.strip().lower()
    if len(text) == 5 and text.isalpha():
        await process_word_choice(update, context, user_id, text)
    elif set(text).issubset({"0", "1", "2"}) and len(text) == 5:
        await process_pattern(update, context, user_id, text)
    else:
        await send_message(update, "Я не понял. Напиши слово (5 букв) или результат вида 02120.")

# 02120
async def process_pattern(update, context, user_id, pattern):
    session = user_sessions.setdefault(user_id, {"history": [], "possible_words": list(WORDS)})
    if not session["history"]:
        await send_message(update, "Сначала введи слово.")
        return

    last = session["history"][-1]
    last["pattern"] = pattern
    session["possible_words"] = filter_words(session["possible_words"], last["word"], pattern)
    history_text = "\n".join(format_history(h["word"], h["pattern"]) for h in session["history"])
    remaining_count = len(session["possible_words"])

    if remaining_count > 0:
        top_words = random.sample(session["possible_words"], min(5, remaining_count))
        buttons = [[InlineKeyboardButton(w.upper(), callback_data=f"word_{w}")] for w in top_words]
        reply_markup = InlineKeyboardMarkup(buttons + list(game_menu().inline_keyboard))
    else:
        reply_markup = game_menu()

    await send_message(update,
        f"Вот твоя история:\n{history_text}\n\nОсталось {remaining_count} слов.",
        reply_markup=reply_markup
    )

def format_history(word, pattern):
    if not pattern:
        return word.upper()
    colors = {"0":"⬜", "1":"🟩", "2":"🟨"}
    return "".join(colors[c] for c in pattern) + f" = {word.upper()}"

def filter_words(words, last_word, pattern):
    return [w for w in words if is_match(w, last_word, pattern)]

from collections import Counter

def is_match(word, target, pattern):
    word_counter = Counter(word)
    # Проверим точные позиции
    for i, (w_c, t_c, p) in enumerate(zip(word, target, pattern)):
        if p == "1":
            if w_c != t_c:
                return False
            word_counter[t_c] -= 1
    # Проверим присутствие в слове (2)
    for i, (w_c, t_c, p) in enumerate(zip(word, target, pattern)):
        if p == "2":
            if w_c == t_c:
                return False
            if word_counter[t_c] <= 0:
                return False
            word_counter[t_c] -= 1
    # Проверим отсутствие (0)
    for i, (w_c, t_c, p) in enumerate(zip(word, target, pattern)):
        if p == "0":
            if word_counter[t_c] > 0:
                return False
    return True

# Запуск
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("feedback", feedback_start))
    app.add_handler(CallbackQueryHandler(handle_buttons, pattern="^(?!rating_).*"))
    app.add_handler(CallbackQueryHandler(handle_rating, pattern=r'^rating_\d'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
