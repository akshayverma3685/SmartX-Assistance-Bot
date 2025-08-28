# Dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

RUN mkdir -p /app/logs

ENV PYTHONUNBUFFERED=1
ENV RUN_MODE=polling

CMD ["python", "bot.py"]
