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

# Temporary storage for user URLs
user_urls = {}

TEXTS = {
    'uz': {
        'start': "👋 Salom! Men ijtimoiy tarmoqlardan video yuklovchi tezkor botman.\n\n"
                 "Menga **TikTok** yoki **Instagram** videosining havolasini yuboring, men uni darhol yuklab beraman! 🚀\n\n"
                 "Sifatni o'zgartirish uchun /settings buyrug'ini bosing.",
        'settings': "⚙️ Video yuklash sifatini tanlang:",
        'downloading': "⏳ Video yuklanmoqda... Iltimos, kuting.",
        'uploading': "📤 Telegramga yuborilmoqda...",
        'audio_downloading': "⏳ Qo'shiq ajratib olinmoqda...",
        'error': "❌ Xatolik yuz berdi:\n{error}",
        'too_large': "⚠️ Fayl hajmi 50MB dan katta. Telegram botlar faqat 50MB gacha qabul qiladi.",
        'quality_updated': "✅ Sifat o'zgartirildi: {quality_text}",
        'unsupported': "⚠️ Kechirasiz, bu bot faqat **TikTok** va **Instagram** havolalarini yuklay oladi!"
    }
}

def get_text(user_id, key, **kwargs):
    text = TEXTS['uz'].get(key, "Xabar topilmadi")
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
        [InlineKeyboardButton(text="🥇 Eng yuqori sifat", callback_data="qual_best")],
        [InlineKeyboardButton(text="🥈 O'rta sifat", callback_data="qual_medium")],
        [InlineKeyboardButton(text="🥉 Past sifat", callback_data="qual_worst")]
    ])
    await message.answer(get_text(user_id, 'settings'), reply_markup=markup)

@dp.callback_query(F.data.startswith("qual_"))
async def process_qual(callback: CallbackQuery):
    qual = callback.data.split("_")[1]
    set_user_settings(callback.from_user.id, quality=qual)
    
    qual_text = "Yuqori" if qual == 'best' else ("O'rta" if qual == 'medium' else "Past")
    await callback.message.edit_text(get_text(callback.from_user.id, 'quality_updated', quality_text=qual_text))
    await callback.answer()

@dp.message(F.text.regexp(r'(https?://[^\s]+)'))
async def handle_url(message: types.Message):
    url = message.text.strip()
    user_id = message.from_user.id
    
    if 'tiktok.com' not in url.lower() and 'instagram.com' not in url.lower():
        await message.reply(get_text(user_id, 'unsupported'))
        return
        
    user_urls[user_id] = url
    msg = await message.reply(get_text(user_id, 'downloading'))
    
    settings = get_user_settings(user_id)
    quality = settings.get('quality', 'best')
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, download_media, url, user_id, quality, 'video')
    
    if result['status'] == 'error':
        await msg.edit_text(get_text(user_id, 'error', error=result['message']))
        return
        
    await msg.edit_text(get_text(user_id, 'uploading'))
    
    try:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎵 Qo'shiqni yuklash", callback_data="get_audio")]
        ])
        
        if result['type'] == 'url':
            try:
                await bot.send_video(chat_id=user_id, video=result['url'], caption=result.get('title', 'Video'), reply_markup=markup)
                await msg.delete()
                return
            except Exception:
                await msg.edit_text("⏳ Telegram URL qabul qilmadi. Fayl qilib tortilmoqda...")
                result = await loop.run_in_executor(None, download_media, url, user_id, quality, 'video_force_dl')
                if result['status'] == 'error':
                    await msg.edit_text(get_text(user_id, 'error', error=result['message']))
                    return
                
        # Handle file upload
        filepath = result.get('filepath')
        if filepath and os.path.exists(filepath):
            if os.path.getsize(filepath) > 50 * 1024 * 1024:
                delete_file(filepath)
                await msg.edit_text(get_text(user_id, 'too_large'))
                return
                
            await bot.send_video(chat_id=user_id, video=FSInputFile(filepath), caption=result.get('title', 'Video'), reply_markup=markup)
            delete_file(filepath)
            await msg.delete()
            
    except Exception as e:
        await msg.edit_text(get_text(user_id, 'error', error=str(e)))
        if result.get('type') == 'file' and 'filepath' in result:
            delete_file(result['filepath'])

@dp.callback_query(F.data == "get_audio")
async def process_get_audio(callback: CallbackQuery):
    user_id = callback.from_user.id
    url = user_urls.get(user_id)
    if not url:
        await callback.answer("Havola topilmadi. Videoni boshqadan yuboring.", show_alert=True)
        return
        
    msg = await callback.message.reply(get_text(user_id, 'audio_downloading'))
    await callback.answer()
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, download_media, url, user_id, 'best', 'audio')
    
    if result['status'] == 'error':
        await msg.edit_text(get_text(user_id, 'error', error=result['message']))
        return
        
    await msg.edit_text(get_text(user_id, 'uploading'))
        
    filepath = result.get('filepath')
    if filepath and os.path.exists(filepath):
        if os.path.getsize(filepath) > 50 * 1024 * 1024:
            delete_file(filepath)
            await msg.edit_text(get_text(user_id, 'too_large'))
            return
            
        await bot.send_audio(chat_id=user_id, audio=FSInputFile(filepath), title=result.get('title', 'Audio'))
        delete_file(filepath)
        await msg.delete()

async def main():
    init_db()
    keep_alive()
    if not bot:
        print("BOT_TOKEN o'rnatilmagan! Iltimos, .env faylida bot tokenini ko'rsating.")
        return
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
