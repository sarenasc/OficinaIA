FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml alembic.ini ./
COPY backend ./backend
RUN pip install --no-cache-dir .
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 38080"]
