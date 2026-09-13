import asyncio
import logging
import os
import yt_dlp
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8686491907:AAF_o7V3oErJXJzxqHSolDfY9b6v2gvVybw"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Временное хранилище ссылок пользователей
user_links = {}

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 **Привет!**\n\n"
        "Я умею скачивать видео, фото и музыку из TikTok, YouTube и других соцсетей!\n\n"
        "Просто отправь мне ссылку!"
    )

# Ловим отправленные ссылки
@dp.message(F.text.regexp(r'https?://[^\s]+'))
async def handle_url(message: types.Message):
    url = message.text.strip()
    user_links[message.from_user.id] = url
    
    # Создаем инлайн-клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 Аудио · MP3", callback_data="dl_audio")],
        [InlineKeyboardButton(text="🎬 Видео / Медиа", callback_data="dl_video")]
    ])
    
    await message.answer("🎬 Что скачиваем?", reply_markup=keyboard)

# Обработка нажатия на кнопки выбора
@dp.callback_query(F.data.startswith("dl_"))
async def process_download(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_links:
        await callback.message.edit_text("❌ Ссылка устарела или не найдена. Отправь её заново.")
        return

    url = user_links[user_id]
    action = callback.data
    
    # Если это ссылка на фото-слайдшоу TikTok, а пользователь нажал «Видео», 
    # предупредим его и скачаем аудиодорожку трека, так как слайды видеоформатом не скачать.
    is_tiktok_photo = "/photo/" in url
    
    if action == "dl_video" and is_tiktok_photo:
        await callback.message.edit_text("🎵 Это фото-слайдшоу TikTok. Скачиваю фоновую музыку из него...")
        action = "dl_audio"  # Принудительно переключаем на скачивание аудио
    else:
        await callback.message.edit_text("📥 Скачиваю...")

    loop = asyncio.get_running_loop()
    
    try:
        if action == "dl_video":
            file_path = await loop.run_in_executor(None, download_video, url)
            if file_path and os.path.exists(file_path):
                await callback.message.edit_text("📤 Отправляю...")
                await callback.message.answer_video(
                    types.FSInputFile(file_path), 
                    caption="Скачано с помощью Mimiks Bot 🤖"
                )
                os.remove(file_path)
                await callback.message.delete()
            else:
                await callback.message.edit_text("❌ Не удалось скачать видео.")
                
        elif action == "dl_audio":
            file_path = await loop.run_in_executor(None, download_audio, url)
            if file_path and os.path.exists(file_path):
                await callback.message.edit_text("📤 Отправляю...")
                await callback.message.answer_audio(
                    types.FSInputFile(file_path), 
                    caption="Скачано с помощью Mimiks Bot 🤖 (Музыка из слайд-шоу)"
                )
                os.remove(file_path)
                await callback.message.delete()
            else:
                await callback.message.edit_text("❌ Не удалось скачать аудио.")
                
    except Exception as e:
        print(f"DEBUG ERROR: {e}")
        await callback.message.edit_text(f"⚠️ Ошибка: контент защищен или недоступен.")

def get_ydl_base_opts():
    return {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'noplaylist': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
    }

def download_video(url):
    opts = get_ydl_base_opts()
    opts['format'] = 'best/bestvideo+bestaudio'
    
    os.makedirs('downloads', exist_ok=True)
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        
        if os.path.exists(filename):
            return filename
        
        base, _ = os.path.splitext(filename)
        for ext in ['.mp4', '.mkv', '.webm', '.mov']:
            if os.path.exists(base + ext):
                return base + ext
                
        return filename

def download_audio(url):
    opts = get_ydl_base_opts()
    opts['format'] = 'ba/best'
    opts['postprocessors'] = [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }]
    
    os.makedirs('downloads', exist_ok=True)
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        base, _ = os.path.splitext(filename)
        return base + ".mp3"

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())