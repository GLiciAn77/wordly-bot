FROM python:3.12-slim

# 1. создаём директорию
WORKDIR /app

# 2. копируем файлы зависимостей и ставим их
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir poetry && \
    poetry install --no-root --no-dev

# 3. копируем остальной код бота
COPY . .

# 4. запускаем
CMD ["poetry", "run", "python", "bot.py"]
