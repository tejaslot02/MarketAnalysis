FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY config ./config
COPY core ./core
COPY ai ./ai
COPY api/app ./api/app

EXPOSE 8000

CMD ["uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
