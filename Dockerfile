FROM python:3.10-slim

WORKDIR /app

# تثبيت الأدوات اللازمة
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# نسخ الملفات
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# تشغيل البوت بنظام Polling (أسهل في Hugging Face)
CMD ["python", "bot.py"]
