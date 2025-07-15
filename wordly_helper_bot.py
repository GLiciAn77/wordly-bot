import os
import re
import datetime
from collections import Counter
from telegram import Update, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Загрузка словаря
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, "five_letter_words.txt")

with open(file_path, encoding="utf-8") as f:
    ALL_WORDS = [line.strip().lower() for line in f if len(line.strip()) == 5]

# Сессии пользователей
sessions = {}

def init_user_session(user_id):
    sessions[user_id] = {
        "possible_words": ALL_WORDS.copy(),
        "awaiting_feedback_text": False,
        "awaiting_feedback_rating": False,
        "temp_feedback_text": "",
        "history": []
    }

def calculate_letter_frequencies(words):
    counter = Counter()
    for word in words:
        counter.update(set(word))
    return counter

def best_start_words(words, top_n=5):
    letter_freq = calculate_letter_frequencies(words)
    scores = []
    for word in words:
        unique_letters = set(word)
        score = sum(letter_freq[c] for c in unique_letters)
        scores.append((score, word))
    scores.sort(reverse=True)
    return [w for s, w in scores[:top_n]]

def render_grid(history):
    lines = []
    emoji_map = {0: "⬜", 1: "🟩", 2: "🟨"}
    for i, (word, feedback) in enumerate(history, 1):
        line = "".join(emoji_map[f] for f in feedback) + " " + word.upper()
        lines.append(f"{i}. {line}")
    for _ in range(5 - len(history)):
        lines.append("⬜⬜⬜⬜⬜")
    return "\n".join(lines)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    init_user_session(user_id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Начать игру", callback_data="new_game")],
        [InlineKeyboardButton("🔍 Помощь", callback_data="help")],
        [InlineKeyboardButton("✍ Оставить отзыв", callback_data="feedback")]
    ])
    await update.message.reply_text(
        "👋 Привет! Я помогу тебе отгадать слово в игре «5 букв»!\n"
        "Просто выбирай слова и присылай результат, а я буду сужать список возможных.\n\n"
        "Выбери действие ниже:",
        reply_markup=keyboard
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def newgame(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback=False):
    user_id = update.effective_user.id
    if user_id not in sessions:
        init_user_session(user_id)
    sessions[user_id]["possible_words"] = ALL_WORDS.copy()
    sessions[user_id]["history"] = []
    best_words = best_start_words(ALL_WORDS)
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(w.upper(), callback_data=f"try_{w}")] for w in best_words] +
        [[InlineKeyboardButton("🎉 Слово отгадано!", callback_data="word_guessed")]]
    )
    text = "🎯 Новая игра!\nВыбери слово для первой попытки или напиши своё:"
    if from_callback:
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)
    else:
        await update.message.reply_text(text, reply_markup=keyboard)

async def handle_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if sessions.get(user_id, {}).get("awaiting_feedback_text"):
        sessions[user_id]["temp_feedback_text"] = text
        sessions[user_id]["awaiting_feedback_text"] = False
        sessions[user_id]["awaiting_feedback_rating"] = True

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("1 💩", callback_data="feedback_1"),
                InlineKeyboardButton("2 😕", callback_data="feedback_2"),
                InlineKeyboardButton("3 🙂", callback_data="feedback_3"),
                InlineKeyboardButton("4 👍", callback_data="feedback_4"),
                InlineKeyboardButton("5 🚀", callback_data="feedback_5"),
            ]
        ])
        await update.message.reply_text(
            "🙏 Спасибо за твой отзыв!\n\n"
            "А теперь оцени меня от 1 до 5, где:\n"
            "1 — отстой 💩\n"
            "5 — супер 🚀",
            reply_markup=keyboard
        )
        return

    if user_id not in sessions:
        init_user_session(user_id)

    # остальной геймплей - можешь вставить свою обработку guess

async def handle_inline_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "new_game":
        await newgame(update, context, from_callback=True)

    elif data == "help":
        await start(update, context)

    elif data == "feedback":
        if user_id not in sessions:
            init_user_session(user_id)
        sessions[user_id]["awaiting_feedback_text"] = True
        await query.edit_message_text("✍ Напиши свой отзыв или пожелания. Я всё прочту и учту!")

    elif data.startswith("feedback_"):
        rating = data[-1]
        text = sessions[user_id].get("temp_feedback_text", "")
        with open("feedback_log.txt", "a", encoding="utf-8") as fout:
            fout.write(f"[{datetime.datetime.now()}] FEEDBACK: {text}\nRATING: {rating}\n\n")
        await query.edit_message_text("✅ Спасибо! Я записал твой отзыв и оценку.")
        sessions[user_id]["awaiting_feedback_rating"] = False
        sessions[user_id]["temp_feedback_text"] = ""

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("newgame", newgame))
    app.add_handler(CommandHandler("feedback", feedback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_word))
    app.add_handler(CallbackQueryHandler(handle_inline_buttons))
    app.run_polling()