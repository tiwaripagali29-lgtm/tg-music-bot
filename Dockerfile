FROM python:3.9-slim

# System tools, FFmpeg, aur NodeJS 18 install karne ke liye
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    gcc \
    git \
    python3-dev \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -U pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
