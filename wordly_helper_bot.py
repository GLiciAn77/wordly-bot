from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from collections import Counter
import os
import re

# Загружаем слова из файла
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, "five_letter_words.txt")

with open(file_path, encoding="utf-8") as f:
    ALL_WORDS = [line.strip().lower() for line in f if len(line.strip()) == 5]

# Состояния пользователей
sessions = {}

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я твой ассистент для Wordly.\n"
        "Напиши /newgame чтобы начать."
    )

async def newgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sessions[user_id] = {
        "possible_words": ALL_WORDS.copy()
    }
    best_words = best_start_words(sessions[user_id]["possible_words"])
    keyboard = [[w] for w in best_words]
    keyboard.append(["Слово угадано!"])
    await update.message.reply_text(
        "🎯 Новая игра!\n"
        "Выбери слово для первой попытки или напиши своё:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )

async def handle_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    word = update.message.text.strip().lower()

    if user_id not in sessions:
        await update.message.reply_text("Сначала начни с /newgame.")
        return

    if word == "слово угадано!":
        await update.message.reply_text(
            "🎉 Отлично! Слово угадано!\n"
            "Хочешь сыграть ещё? Напиши /newgame.",
            reply_markup=ReplyKeyboardRemove()
        )
        sessions.pop(user_id, None)
        return

    if len(word) != 5:
        await update.message.reply_text("Слово должно быть из 5 букв.")
        return

    sessions[user_id]["last_word"] = word
    await update.message.reply_text(
        f"✍ Пришли результат для слова *{word}*.\n"
        "Формат: `01210` (1 — 🟩, 2 — 🟨, 0 — ⬜)\n"
        "или эмодзи: ⬜🟩🟨⬜🟩",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in sessions or "last_word" not in sessions[user_id]:
        await update.message.reply_text("Сначала выбери слово.")
        return

    feedback = update.message.text.strip()

    if re.match(r"^[012]{5}$", feedback):
        feedback_list = [int(c) for c in feedback]
    else:
        emoji_to_digit = {"⬜":0, "🟩":1, "🟨":2}
        feedback_list = [emoji_to_digit.get(c, -1) for c in feedback]
        if -1 in feedback_list or len(feedback_list) != 5:
            await update.message.reply_text("Формат не распознан. Используй `01210` или ⬜🟩🟨.")
            return

    # проверка на победу
    if all(fb == 1 for fb in feedback_list):
        await update.message.reply_text(
            "🎉 Отлично! Слово угадано!\n"
            "Хочешь сыграть ещё? Напиши /newgame.",
            reply_markup=ReplyKeyboardRemove()
        )
        sessions.pop(user_id, None)
        return

    tried_word = sessions[user_id]["last_word"]
    new_possible = []

    for word in sessions[user_id]["possible_words"]:
        match = True
        for i, (ch, fb) in enumerate(zip(tried_word, feedback_list)):
            if fb == 1:
                if word[i] != ch:
                    match = False
                    break
            elif fb == 2:
                if ch not in word or word[i] == ch:
                    match = False
                    break
            elif fb == 0:
                count_in_feedback = sum(1 for k, f in enumerate(feedback_list) if tried_word[k] == ch and f in (1,2))
                if word.count(ch) > count_in_feedback:
                    match = False
                    break
        if match:
            new_possible.append(word)

    sessions[user_id]["possible_words"] = new_possible

    if not new_possible:
        await update.message.reply_text("😕 Не нашёл подходящих слов. Возможно ошибка во вводе.")
    else:
        best_words = best_start_words(new_possible)
        keyboard = [[w] for w in best_words]
        keyboard.append(["Слово угадано!"])
        await update.message.reply_text(
            f"🔎 После фильтрации осталось {len(new_possible)} слов.\n"
            "Выбери слово для следующей попытки или напиши своё:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )

def main():
    app = ApplicationBuilder().token("7708015298:AAGFBGvQvEgPFJmfJ43AAPj99k9tWbwP09k").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newgame", newgame))
    app.add_handler(MessageHandler(filters.Regex(r"^[012⬜🟩🟨]{5}$"), handle_feedback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_word))
    app.run_polling()

if __name__ == "__main__":
    main()
