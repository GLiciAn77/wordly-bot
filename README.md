# Wordly Bot 🇷🇺

Телеграм-бот для помощи в игре «5 букв» (аналог Wordle), на русском языке, с учётом повторяющихся букв и оптимальным подбором слов.

## 🚀 Запуск в Docker
git clone https://github.com/GLiciAn77/wordly-bot.git
cd wordly-bot
docker compose up -d


## 📲 Использование
* /newgame — начать игру
* выбрать слово кнопкой или ввести своё
* прислать результат (например 01210 или ⬜🟩🟨)
* бот предложит следующие слова


---

## 📄 five_letter_words.txt
(это твой список слов из 5 букв, который мы уже готовили. Просто положи в проект.)

---

## 📄 wordly_helper_bot.py
(это твой улучшенный бот с кнопками, «Слово угадано!» и т.д.)

Если хочешь — могу прямо сейчас **собрать всё это в один ZIP**, чтобы ты просто скачал, распаковал и сделал:

```bash
git init
git remote add origin https://github.com/GLiciAn77/wordly-bot.git
git add .
git commit -m "initial bot"
git push -u origin main

## ⚙ Конфигурация
Все зависимости уже указаны в Dockerfile, нужен только Docker.

---
👨‍💻 Сделано с ❤️ by GLiciAn77
