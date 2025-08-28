# Dockerfile
FROM python:3.11-slim

# system deps for ffmpeg and yt-dlp, and build essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# install python deps
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# create logs dir
RUN mkdir -p /app/logs

ENV PYTHONUNBUFFERED=1
ENV RUN_MODE=polling

# default command: run bot.py
CMD ["python", "bot.py"]
