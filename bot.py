import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.types import Message

# ==================== تنظیمات ====================
BOT_TOKEN = "8987932948:AAGt6fWBkV6rBarvFAVJizlKdcvjuqGLErQ"
CUSTOM_EMOJI_ID = "5368324170671202286"

# ==================== راه‌اندازی ====================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==================== کیبورد با کاستوم ایموجی ====================
keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Primary",
                callback_data="primary",
                icon_custom_emoji_id=CUSTOM_EMOJI_ID  # این خط رو اضافه کن
            )
        ],
        [
            InlineKeyboardButton(
                text="Success",
                callback_data="success",
                icon_custom_emoji_id=CUSTOM_EMOJI_ID
            )
        ],
        [
            InlineKeyboardButton(
                text="Danger",
                callback_data="danger",
                icon_custom_emoji_id=CUSTOM_EMOJI_ID
            )
        ]
    ]
)

# ==================== دستور /start ====================
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "👋 سلام! این یک دکمه با کاستوم ایموجی است:",
        reply_markup=keyboard
    )

# ==================== هندلر دکمه‌ها ====================
@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    data = callback.data
    await callback.answer(f"✅ دکمه {data} کلیک شد!", show_alert=True)
    await callback.message.answer(f"👀 شما روی دکمه **{data}** کلیک کردید!")

# ==================== اجرا ====================
async def main():
    print("🤖 ربات با Aiogram روشن شد!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
