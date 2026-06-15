import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
from dotenv import load_dotenv

from keep_alive import keep_alive
from database import init_db, get_user_settings, set_user_settings
from downloader import download_media, delete_file

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

logging.basicConfig(level=logging.INFO)

if BOT_TOKEN and BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE':
    bot = Bot(token=BOT_TOKEN)
else:
    bot = None
    
dp = Dispatcher()

# Temporary storage for user URLs to avoid 64-byte callback limit
user_urls = {}

TEXTS = {
    'uz': {
        'start': "Salom! Menga istalgan video havolasini yuboring (YouTube, Instagram, TikTok va boshqalar), men uni yuklab beraman.\n\nSiz sifatni va tilni sozlash uchun /settings buyrug'idan foydalanishingiz mumkin.",
        'settings': "⚙️ Sozlamalar menyusi:",
        'downloading': "⏳ Yuklanmoqda... Iltimos, kuting.",
        'uploading': "📤 Telegramga yuklanmoqda...",
        'error': "❌ Xatolik yuz berdi:\n{error}",
        'too_large': "⚠️ Fayl hajmi 50MB dan katta. Telegram botlar faqat 50MB gacha fayl qabul qiladi.",
        'quality_updated': "✅ Sifat o'zgartirildi: {quality}",
        'lang_updated': "✅ Til o'zgartirildi: {lang}",
        'choose_action': "🔽 Nimani yuklab olamiz?"
    },
    'ru': {
        'start': "Привет! Отправьте мне любую ссылку на видео, и я скачаю его.\n\nИспользуйте /settings для настроек.",
        'settings': "⚙️ Настройки:",
        'downloading': "⏳ Скачивается... Пожалуйста, подождите.",
        'uploading': "📤 Загрузка в Telegram...",
        'error': "❌ Произошла ошибка:\n{error}",
        'too_large': "⚠️ Размер файла превышает 50 МБ.",
        'quality_updated': "✅ Качество обновлено: {quality}",
        'lang_updated': "✅ Язык изменен: {lang}",
        'choose_action': "🔽 Что сделать?"
    }
}

def get_text(user_id, key, **kwargs):
    settings = get_user_settings(user_id)
    lang = settings.get('language', 'uz')
    if lang not in TEXTS:
        lang = 'uz'
    text = TEXTS[lang].get(key, TEXTS['uz'][key])
    return text.format(**kwargs)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    get_user_settings(user_id) # init user in db
    await message.answer(get_text(user_id, 'start'))

@dp.message(Command("settings"))
async def cmd_settings(message: types.Message):
    user_id = message.from_user.id
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang_uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")
        ],
        [
            InlineKeyboardButton(text="📉 Eng past sifat", callback_data="qual_worst"),
            InlineKeyboardButton(text="📈 Eng yuqori sifat", callback_data="qual_best")
        ]
    ])
    await message.answer(get_text(user_id, 'settings'), reply_markup=markup)

@dp.callback_query(F.data.startswith("lang_"))
async def process_lang(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    set_user_settings(callback.from_user.id, language=lang)
    await callback.message.edit_text(get_text(callback.from_user.id, 'lang_updated', lang=lang))
    await callback.answer()

@dp.callback_query(F.data.startswith("qual_"))
async def process_qual(callback: CallbackQuery):
    qual = callback.data.split("_")[1]
    set_user_settings(callback.from_user.id, quality=qual)
    await callback.message.edit_text(get_text(callback.from_user.id, 'quality_updated', quality=qual))
    await callback.answer()

@dp.message(F.text.regexp(r'(https?://[^\s]+)'))
async def handle_url(message: types.Message):
    url = message.text.strip()
    user_id = message.from_user.id
    user_urls[user_id] = url
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Video", callback_data="action_video"),
            InlineKeyboardButton(text="🎵 Audio (MP3)", callback_data="action_audio")
        ]
    ])
    await message.reply(get_text(user_id, 'choose_action'), reply_markup=markup)

@dp.callback_query(F.data.startswith("action_"))
async def process_action(callback: CallbackQuery):
    action = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    url = user_urls.get(user_id)
    if not url:
        await callback.answer("Havola eskirgan. Iltimos, havolani qayta yuboring.", show_alert=True)
        return
        
    await callback.message.edit_text(get_text(user_id, 'downloading'))
    
    settings = get_user_settings(user_id)
    quality = settings.get('quality', 'best')
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, download_media, url, user_id, quality, action)
    
    if result['status'] == 'error':
        await callback.message.edit_text(get_text(user_id, 'error', error=result['message']))
        return
        
    await callback.message.edit_text(get_text(user_id, 'uploading'))
    
    try:
        if result['type'] == 'url':
            try:
                await bot.send_video(chat_id=user_id, video=result['url'], caption=result.get('title', 'Video'))
                await callback.message.delete()
                return
            except Exception as e:
                # Telegram URL qabul qilmadi (masalan YouTube himoyasi), fayl qilib tortamiz
                await callback.message.edit_text("⏳ Telegram to'g'ridan-to'g'ri havolani qabul qilmadi. Kompyuterga saqlab yuborilmoqda (bu biroz vaqt oladi)...")
                result = await loop.run_in_executor(None, download_media, url, user_id, quality, 'video_force_dl')
                if result['status'] == 'error':
                    await callback.message.edit_text(get_text(user_id, 'error', error=result['message']))
                    return
                
        # Handle file upload
        filepath = result.get('filepath')
        if filepath and os.path.exists(filepath):
            if os.path.getsize(filepath) > 50 * 1024 * 1024:
                delete_file(filepath)
                await callback.message.edit_text(get_text(user_id, 'too_large'))
                return
                
            await callback.message.edit_text(get_text(user_id, 'uploading'))
            if action == 'audio':
                await bot.send_audio(chat_id=user_id, audio=FSInputFile(filepath), title=result.get('title', 'Audio'))
            else:
                await bot.send_video(chat_id=user_id, video=FSInputFile(filepath), caption=result.get('title', 'Video'))
            delete_file(filepath)
            await callback.message.delete()
            
    except Exception as e:
        await callback.message.edit_text(get_text(user_id, 'error', error=str(e)))
        if result.get('type') == 'file' and 'filepath' in result:
            delete_file(result['filepath'])

async def main():
    init_db()
    keep_alive()
    if not bot:
        print("BOT_TOKEN o'rnatilmagan! Iltimos, .env faylida bot tokenini ko'rsating.")
        return
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
