# သတ်မှတ်ချက်အရ ပေါ့ပါးပြီ အဆင်ပြေမည့် Python Base Image ကို သုံးပါမည်
FROM python:3.10-slim

# စနစ်အတွက် လိုအပ်သော Linux packages များနှင့် OpenCV/ddddocr အတွက် လိုအပ်သော libraries များကို သွင်းပါမည်
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libpng-dev \
    libjpeg-dev \
    libtesseract-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# အလုပ်လုပ်မည့် App Directory ကို သတ်မှတ်ပါမည်
WORKDIR /app

# လိုအပ်သော Python Package များကို အဆင့်ဆင့် သွင်းပါမည်
# OpenCV အတွက် Render/Koyeb ပေါ်တွင် အဆင်ပြေဆုံးဖြစ်သော headless version ကို သုံးပါမည်
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir pyTelegramBotAPI aiohttp numpy opencv-python-headless ddddocr

# သင့်ရဲ့ Code ဖိုင်များအားလုံးကို Docker Container ထဲသို့ ကူးထည့်ပါမည်
COPY . .

# Ruijie Bot ထဲတွင် Port 8080 ဖြင့် Web Server ဖွင့်ထားသဖြင့် Port ကို ဖွင့်ပေးရပါမည်
EXPOSE 8080

# Bot စတင် Run မည့် Command ဖြစ်ပါသည် (သင့်ဖိုင်နာမည် kok9.py နှင့် ကိုက်ညီအောင် ထည့်ထားပါသည်)
CMD ["python", "bot.py"]