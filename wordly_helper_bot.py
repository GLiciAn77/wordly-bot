from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from collections import Counter
import os
import re
import datetime

# Загрузка словаря
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, "five_letter_words.txt")

with open(file_path, encoding="utf-8") as f:
    ALL_WORDS = [line.strip().lower() for line in f if len(line.strip()) == 5]

# Хранение сессий
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
    await help_command(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Справка по командам\n\n"
        "/newgame — начать новую игру и получить список слов для первой попытки.\n"
        "/stats — показать, сколько слов в словаре.\n"
        "/help — вывести эту справку.\n"
        "/feedback <текст> — оставить отзыв или предложение.\n\n"
        "После каждой попытки присылай результат:\n"
        "⬜🟩🟨 или например 01210.\n\n"
        "Ты можешь выбрать слово из кнопок или написать своё."
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📊 Сейчас в словаре {len(ALL_WORDS)} слов из 5 букв.")

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ' '.join(context.args)
    if not text:
        await update.message.reply_text("✍ Напиши после /feedback свой комментарий.")
        return
    with open("feedback_log.txt", "a", encoding="utf-8") as fout:
        fout.write(f"[{datetime.datetime.now()}] FEEDBACK: {text}\n")
    await update.message.reply_text("✅ Спасибо! Я записал твоё сообщение.")

async def newgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sessions[user_id] = {
        "possible_words": ALL_WORDS.copy(),
        "awaiting_unknown_confirm": None
    }
    best_words = best_start_words(sessions[user_id]["possible_words"])
    keyboard = [[w] for w in best_words]
    keyboard.append(["Слово угадано!"])
    await update.message.reply_text(
        "🎯 Новая игра!\nВыбери слово для первой попытки или напиши своё:",
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
            "🎉 Отлично! Слово угадано!\nХочешь сыграть ещё? Напиши /newgame.",
            reply_markup=ReplyKeyboardRemove()
        )
        sessions.pop(user_id, None)
        return

    # Если ожидаем подтверждения
    if sessions[user_id].get("awaiting_unknown_confirm"):
        if word == "✅ всё верно":
            unknown_word = sessions[user_id]["awaiting_unknown_confirm"]
            with open("feedback_log.txt", "a", encoding="utf-8") as fout:
                fout.write(f"[{datetime.datetime.now()}] USER confirmed unknown word '{unknown_word}' as valid.\n")
            await update.message.reply_text("✅ Записал в журнал и продолжаем.")
            sessions[user_id]["awaiting_unknown_confirm"] = None
        elif word == "🔄 ввести другое слово":
            sessions[user_id]["awaiting_unknown_confirm"] = None
            await update.message.reply_text("✍ Напиши другое слово:")
            return
        else:
            await update.message.reply_text("😕 Выбери один из вариантов: ✅ или 🔄.")
            return

    # Если слово не найдено в возможных
    if word not in sessions[user_id]["possible_words"]:
        sessions[user_id]["awaiting_unknown_confirm"] = word
        keyboard = [["✅ Всё верно"], ["🔄 Ввести другое слово"]]
        await update.message.reply_text(
            f"🤔 Я не нашёл слова «{word}» в своём словаре. Ты уверен, что написал правильно?",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return

    sessions[user_id]["last_word"] = word
    await update.message.reply_text(
        f"✍ Теперь пришли результат для слова *{word}* в формате `01210` или ⬜🟩🟨.",
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

    if all(fb == 1 for fb in feedback_list):
        await update.message.reply_text(
            "🎉 Отлично! Слово угадано!\nХочешь сыграть ещё? Напиши /newgame.",
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

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤔 Я тебя не понял. Вот что ты можешь сделать:\n\n"
        "/newgame — начать новую игру\n"
        "/stats — посмотреть словарь\n"
        "/help — справка\n"
        "/feedback <текст> — оставить отзыв."
    )

def main():
    app = ApplicationBuilder().token("7708015298:AAGFBGvQvEgPFJmfJ43AAPj99k9tWbwP09k").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command)) #добавил помощь
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("feedback", feedback)) #добавил фидбек
    app.add_handler(CommandHandler("newgame", newgame))
    app.add_handler(MessageHandler(filters.Regex(r"^[012⬜🟩🟨]{5}$"), handle_feedback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_word))
    app.add_handler(MessageHandler(filters.ALL, unknown))
    app.run_polling()

if __name__ == "__main__":
    main()