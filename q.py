import asyncio
import io
import re
import cv2
import numpy as np
import easyocr

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart

BOT_TOKEN = "8904060069:AAG_O07cA7pPJByw1GtoGjuJplKTuJ5055c"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Налаштовуємо розпізнавання
reader = easyocr.Reader(['en'])

# Словник виправлення частих помилок шрифту Brawl Stars
CHAR_FIXES = {
    'Z': '2',
    'I': '9',
    'C': 'G',
    'O': '0',
    'S': '5',
    'B': '8'
}

def preprocess_and_read(image_bytes):
    # Конвертуємо байти в масив OpenCV
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Переводимо в сірий колір та збільшуємо контраст
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Збільшуємо розмір у 2 рази для чіткості дрібного тексту
    resized = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    # Застосовуємо поріг білого (Thresholding), щоб зробити текст виразно білим на чорному фоні
    _, thresh = cv2.threshold(resized, 150, 255, cv2.THRESH_BINARY)

    # Зчитуємо текст із двох варіантів (оригінал та оброблений)
    results_raw = reader.readtext(resized, detail=0)
    results_thresh = reader.readtext(thresh, detail=0)
    
    combined_text = " ".join(results_raw + results_thresh).upper()
    return combined_text

@dp.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer("👋 Надішли мені скріншот профілю Brawl Stars!", parse_mode="Markdown")

@dp.message(F.photo)
async def scan_tag_from_photo(message: Message):
    status_msg = await message.answer("🔍 *Обробляю фото та зчитую тег...*", parse_mode="Markdown")
    
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    
    try:
        image_bytes = downloaded_file.read()
        raw_text = preprocess_and_read(image_bytes)
        
        # Шукаємо тег
        match = re.search(r'#[0-9A-Z]{3,10}', raw_text)
        
        if match:
            found_tag = match.group(0)
            
            # Автоматично виправляємо плутанину літер та цифр
            fixed_tag = "#"
            for char in found_tag[1:]:
                fixed_tag += CHAR_FIXES.get(char, char)
            
            await status_msg.edit_text(
                f"🏷 **Знайдений тег:**\n`{fixed_tag}`\n\n*(натисни, щоб скопіювати)*",
                parse_mode="Markdown"
            )
        else:
            await status_msg.edit_text("❌ **Тег не знайдено.** Спробуй надіслати скріншот вищої якості.")
            
    except Exception as e:
        await status_msg.edit_text(f"⚠️ **Помилка:** {e}")

async def main():
    print("🤖 Бот із покращеним розпізнаванням запущений!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())