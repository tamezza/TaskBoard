FROM python:3.15-slim

RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y pip

COPY alembic.ini .
COPY migrations/ migrations/
COPY app/ app/

RUN useradd --create-home appuser && chown appuser /app
USER appuser

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log"]