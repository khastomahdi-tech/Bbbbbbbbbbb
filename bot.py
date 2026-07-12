# ============================================
# بخش ۱: ایمپورت‌ها و تنظیمات اولیه
# ============================================

import asyncio
import logging
import sqlite3
import json
import random
import re
import os
import time
from datetime import datetime, timedelta
from io import BytesIO

import pytz
import qrcode
from PIL import Image

from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, 
    InlineKeyboardButton, MessageEntity, BufferedInputFile
)
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher.filters import Command, Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor

# ==================== تنظیمات اولیه ====================
BOT_TOKEN = "8319089742:AAFoU3TT1hmpdiqd70fidyahUS9RG7CpVg4"
OWNER_ID = 7323216202
BOT_USERNAME = "@DEMONFREECONF_BOT"
PING_THRESHOLD = 130
PING_INTERVAL = 60

IRAN_TZ = pytz.timezone('Asia/Tehran')

# کاستوم ایموجی‌ها
EMOJI_GET_SERVER = "5900199258316869673"
EMOJI_MY_SERVICES = "5780806262774042817"
EMOJI_MY_ACCOUNT = "5902172654055460877"
EMOJI_MY_WALLET = "5900199258316869673"
EMOJI_HELP = "5780806262774042817"
EMOJI_ADMIN = "5902172654055460877"
EMOJI_BACK = "5900199258316869673"
EMOJI_QR = "5780806262774042817"
EMOJI_INFO = "5902172654055460877"
EMOJI_CONFIG = "5900199258316869673"
EMOJI_PING = "5780806262774042817"
EMOJI_REPORT = "5902172654055460877"
EMOJI_DELETE = "5900199258316869673"
EMOJI_RENAME = "5780806262774042817"

# ==================== راه‌اندازی ====================
logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=storage)
# ============================================
# بخش ۲: توابع دیتابیس و کمکی
# ============================================

def init_db():
    db = sqlite3.connect("bot.db", check_same_thread=False)
    cursor = db.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id TEXT PRIMARY KEY,
        daily_count INTEGER DEFAULT 0,
        last_reset TEXT,
        servers TEXT DEFAULT '[]',
        first_name TEXT,
        username TEXT,
        joined_at TEXT,
        last_emoji_msg_id TEXT,
        wallet INTEGER DEFAULT 0,
        warnings INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS servers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        config TEXT,
        ip TEXT,
        port TEXT,
        protocol TEXT,
        used_by TEXT,
        expiry TEXT,
        ping INTEGER DEFAULT 0,
        last_ping_check TEXT,
        last_ping_notification TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages(
        name TEXT PRIMARY KEY,
        text TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wallet_transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        amount INTEGER,
        type TEXT,
        description TEXT,
        created_at TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ping_reports(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        server_id TEXT,
        user_id TEXT,
        ping INTEGER,
        reported_at TEXT,
        status TEXT DEFAULT 'pending'
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS server_reports(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        server_id TEXT,
        user_id TEXT,
        report_text TEXT,
        reported_at TEXT,
        status TEXT DEFAULT 'pending'
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bot_settings(
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    db.commit()
    return db, cursor

db, cursor = init_db()

# ==================== توابع کمکی ====================

def get_iran_time():
    return datetime.now(IRAN_TZ)

def format_iran_time(dt):
    return dt.strftime('%Y-%m-%d %H:%M')

def get_iran_time_iso():
    return get_iran_time().isoformat()

def get_user_data(user_id):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM users WHERE user_id=?", (str(user_id),))
        data = c.fetchone()
        if not data:
            return {"daily_count": 0, "last_reset": get_iran_time().isoformat(), "servers": [], "first_name": "", "username": "", "joined_at": get_iran_time().isoformat(), "last_emoji_msg_id": None, "wallet": 0, "warnings": 0, "is_banned": 0}
        
        try:
            last_reset = datetime.fromisoformat(data[2]).date()
        except:
            last_reset = get_iran_time().date()
        
        today = get_iran_time().date()
        if last_reset != today:
            c.execute("UPDATE users SET daily_count=0, last_reset=? WHERE user_id=?", (get_iran_time().isoformat(), str(user_id)))
            conn.commit()
            return {"daily_count": 0, "last_reset": get_iran_time().isoformat(), "servers": json.loads(data[3]) if data[3] else [], "first_name": data[4], "username": data[5], "joined_at": data[6], "last_emoji_msg_id": data[7] if len(data) > 7 else None, "wallet": data[8] if len(data) > 8 else 0, "warnings": data[9] if len(data) > 9 else 0, "is_banned": data[10] if len(data) > 10 else 0}
        
        return {
            "daily_count": data[1],
            "last_reset": data[2],
            "servers": json.loads(data[3]) if data[3] else [],
            "first_name": data[4] if len(data) > 4 else "",
            "username": data[5] if len(data) > 5 else "",
            "joined_at": data[6] if len(data) > 6 else get_iran_time().isoformat(),
            "last_emoji_msg_id": data[7] if len(data) > 7 else None,
            "wallet": data[8] if len(data) > 8 else 0,
            "warnings": data[9] if len(data) > 9 else 0,
            "is_banned": data[10] if len(data) > 10 else 0
        }
    finally:
        conn.close()

def get_user_servers(user_id):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT servers FROM users WHERE user_id=?", (str(user_id),))
        data = c.fetchone()
        if data and data[0]:
            try:
                return json.loads(data[0])
            except:
                return eval(data[0])
        return []
    finally:
        conn.close()

def save_user_servers(user_id, servers_list):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO users(user_id, servers) VALUES(?,?)", (str(user_id), json.dumps(servers_list)))
        conn.commit()
    finally:
        conn.close()

def get_free_servers():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM servers WHERE used_by IS NULL")
        return c.fetchall()
    finally:
        conn.close()

def assign_server_to_user(server_id, user_id):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("UPDATE servers SET used_by=? WHERE id=?", (str(user_id), server_id))
        conn.commit()
    finally:
        conn.close()

def get_wallet(user_id):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT wallet FROM users WHERE user_id=?", (str(user_id),))
        data = c.fetchone()
        return data[0] if data else 0
    finally:
        conn.close()

def add_wallet(user_id, amount):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET wallet = wallet + ? WHERE user_id=?", (amount, str(user_id)))
        conn.commit()
        return get_wallet(user_id)
    finally:
        conn.close()

def get_message(name):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT text FROM messages WHERE name=?", (name,))
        data = c.fetchone()
        return data[0] if data else None
    finally:
        conn.close()

def save_message(name, text):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO messages(name,text) VALUES(?,?)", (name, text))
        conn.commit()
    finally:
        conn.close()

def get_server_name(user_id):
    return f"{user_id}_{BOT_USERNAME}_1GB"

def add_hashtag_to_config(config, user_id, username):
    now = get_iran_time()
    hashtag = f"#{user_id}_{username}_{now.strftime('%Y%m%d')}_نامحدود_1GB"
    return f"{config}{hashtag}"

def get_location_from_ip(ip):
    if ip == "Unknown" or not ip:
        return "نامشخص"
    try:
        import requests
        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return f"{data.get('city', '')}, {data.get('country', '')}"
        return "نامشخص"
    except:
        return "نامشخص"

def create_custom_emoji_button(text, callback_data, emoji_id):
    return InlineKeyboardButton(
        text=text,
        callback_data=callback_data,
        icon_custom_emoji_id=emoji_id
    )
# ============================================
# بخش ۳: کیبوردها و پیام‌ها
# ============================================

def get_main_keyboard(user_id):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        create_custom_emoji_button("📥 دریافت سرور", "get_free_server", EMOJI_GET_SERVER),
        create_custom_emoji_button("📋 سرویس‌های من", "my_services", EMOJI_MY_SERVICES)
    )
    keyboard.add(
        create_custom_emoji_button("👤 حساب کاربری", "my_account", EMOJI_MY_ACCOUNT),
        create_custom_emoji_button("💰 کیف پول", "my_wallet", EMOJI_MY_WALLET)
    )
    keyboard.add(
        create_custom_emoji_button("ℹ️ راهنما", "help", EMOJI_HELP)
    )
    
    if int(user_id) == OWNER_ID:
        keyboard.add(
            create_custom_emoji_button("🔧 پنل مدیریت", "admin_panel", EMOJI_ADMIN)
        )
    
    return keyboard

def get_server_action_keyboard(server_id):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        create_custom_emoji_button("📱 QR Code", f"qr_{server_id}", EMOJI_QR),
        create_custom_emoji_button("📋 مشخصات", f"info_{server_id}", EMOJI_INFO)
    )
    keyboard.add(
        create_custom_emoji_button("📄 کانفیگ", f"config_{server_id}", EMOJI_CONFIG),
        create_custom_emoji_button("📊 پینگ", f"ping_{server_id}", EMOJI_PING)
    )
    keyboard.add(
        create_custom_emoji_button("⚠️ گزارش خرابی", f"report_{server_id}", EMOJI_REPORT),
        create_custom_emoji_button("🗑 حذف سرویس", f"delete_{server_id}", EMOJI_DELETE)
    )
    keyboard.add(
        create_custom_emoji_button("✏️ تغییر نام", f"rename_{server_id}", EMOJI_RENAME),
        create_custom_emoji_button("🔙 بازگشت", "back_to_services", EMOJI_BACK)
    )
    return keyboard

def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📊 آمار", callback_data="admin_stats"),
        InlineKeyboardButton("➕ اضافه کردن", callback_data="admin_add_servers")
    )
    keyboard.add(
        InlineKeyboardButton("🗑 حذف سرور", callback_data="admin_remove_server"),
        InlineKeyboardButton("📋 کاربران", callback_data="admin_users")
    )
    keyboard.add(
        InlineKeyboardButton("✏️ ویرایش پیام‌ها", callback_data="admin_edit_messages"),
        InlineKeyboardButton("📊 پینگ بالا", callback_data="admin_ping_reports")
    )
    keyboard.add(
        InlineKeyboardButton("⚠️ گزارش خرابی", callback_data="admin_server_reports"),
        InlineKeyboardButton("🔄 آپدیت سرویس", callback_data="admin_update_service")
    )
    keyboard.add(
        InlineKeyboardButton("📢 چنل‌های اجباری", callback_data="admin_required_channels"),
        InlineKeyboardButton("💰 مدیریت کیف پول", callback_data="admin_wallet")
    )
    keyboard.add(
        InlineKeyboardButton("⚠️ مدیریت اخطارها", callback_data="admin_warnings"),
        InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
    )
    return keyboard

def get_back_keyboard(callback):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(create_custom_emoji_button("🔙 بازگشت", callback, EMOJI_BACK))
    return keyboard

# ==================== پیام‌های پیش‌فرض ====================

DEFAULT_WELCOME = """
**سلام {first_name} عزیز!**

به ربات مدیریت سرورهای رایگان خوش آمدید!

**با این ربات می‌تونید:**
✅ هر روز ۲ تا سرور رایگان V2Ray بگیرید
✅ سرورهای خودتون رو مدیریت کنید
✅ QR Code و مشخصات سرورها رو ببینید
✅ کیف پول خود را مدیریت کنید

**قوانین:**
• هر کاربر روزانه ۲ سرور دریافت میکنه
• حجم هر سرور: ۱ گیگابایت
• مدت زمان: نامحدود

لطفاً یکی از گزینه‌های زیر رو انتخاب کنید:
# ============================================
# بخش ۴: هندلرهای اصلی
# ============================================

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    username = message.from_user.username or ""
    
    welcome_text = DEFAULT_WELCOME.format(first_name=first_name)
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(user_id),
        parse_mode="HTML"
    )

@dp.callback_query_handler(lambda c: True)
async def handle_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data
    
    if data == "back_to_main":
        first_name = callback.from_user.first_name or ""
        welcome_text = DEFAULT_WELCOME.format(first_name=first_name)
        await callback.message.edit_text(
            welcome_text,
            reply_markup=get_main_keyboard(user_id),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    if data == "get_free_server":
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            create_custom_emoji_button("🟣 V2Ray", "vpn_v2ray", EMOJI_GET_SERVER),
            create_custom_emoji_button("🔙 بازگشت", "back_to_main", EMOJI_BACK)
        )
        await callback.message.edit_text(
            "🔍 **انتخاب نوع سرور:**",
            reply_markup=keyboard
        )
        await callback.answer()
        return
    
    if data == "vpn_v2ray":
        free_servers = get_free_servers()
        
        if not free_servers:
            await callback.message.edit_text(
                "❌ **هیچ سرور آزادی موجود نیست!**\nلطفاً بعداً دوباره تلاش کنید.",
                reply_markup=get_back_keyboard("back_to_main")
            )
            await callback.answer()
            return
        
        selected = random.choice(free_servers)
        server_id = selected[0]
        config = selected[1]
        
        username = callback.from_user.username or f"user{user_id}"
        config_with_hashtag = add_hashtag_to_config(config, user_id, username)
        
        assign_server_to_user(server_id, user_id)
        
        server_name = get_server_name(user_id)
        
        user_servers = get_user_servers(user_id)
        user_servers.append({
            "server_id": server_id,
            "name": server_name,
            "config": config_with_hashtag,
            "ip": selected[2],
            "port": selected[3],
            "protocol": selected[4],
            "received_at": get_iran_time().isoformat(),
            "expiry": None,
            "volume": "1GB",
            "duration": "نامحدود"
        })
        save_user_servers(user_id, user_servers)
        
        await callback.message.edit_text(
            "⏳ **سرور در حال ساخته شدن است...**\nلطفاً چند لحظه صبر کنید."
        )
        await asyncio.sleep(3)
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            create_custom_emoji_button("📋 سرویس‌های من", "my_services", EMOJI_MY_SERVICES),
            create_custom_emoji_button("🔙 بازگشت", "back_to_main", EMOJI_BACK)
        )
        
        await callback.message.edit_text(
            f"✅ **سرویس شما با موفقیت ایجاد شد!**\n\n📌 **نام سرور:** {server_name}",
            reply_markup=keyboard
        )
        await callback.answer()
        return
    
    if data == "my_services":
        user_servers = get_user_servers(user_id)
        
        if not user_servers:
            await callback.message.edit_text(
                "📭 **شما هیچ سرویسی دریافت نکردید!**",
                reply_markup=get_back_keyboard("back_to_main")
            )
            await callback.answer()
            return
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        for server in user_servers:
            keyboard.add(
                InlineKeyboardButton(
                    f"📌 {server['name']} - ✅ فعال",
                    callback_data=f"view_server_{server['server_id']}"
                )
            )
        keyboard.add(
            create_custom_emoji_button("🔙 بازگشت", "back_to_main", EMOJI_BACK)
        )
        
        await callback.message.edit_text(
            "📋 **لیست سرویس‌های شما:**",
            reply_markup=keyboard
        )
        await callback.answer()
        return
    
    if data.startswith("view_server_"):
        server_id = int(data.split("_")[2])
        user_servers = get_user_servers(user_id)
        server = next((s for s in user_servers if s["server_id"] == server_id), None)
        
        if not server:
            await callback.message.edit_text(
                "❌ **سرور مورد نظر یافت نشد!**",
                reply_markup=get_back_keyboard("back_to_main")
            )
            await callback.answer()
            return
        
        await callback.message.edit_text(
            f"📌 **سرور: {server['name']}**\n⏳ وضعیت: ✅ فعال\n📊 حجم: {server['volume']}",
            reply_markup=get_server_action_keyboard(server_id)
        )
        await callback.answer()
        return
    
    if data == "back_to_services":
        user_servers = get_user_servers(user_id)
        keyboard = InlineKeyboardMarkup(row_width=1)
        for server in user_servers:
            keyboard.add(
                InlineKeyboardButton(
                    f"📌 {server['name']} - ✅ فعال",
                    callback_data=f"view_server_{server['server_id']}"
                )
            )
        keyboard.add(
            create_custom_emoji_button("🔙 بازگشت", "back_to_main", EMOJI_BACK)
        )
        
        await callback.message.edit_text(
            "📋 **لیست سرویس‌های شما:**",
            reply_markup=keyboard
        )
        await callback.answer()
        return
    
    if data == "my_account":
        user_data = get_user_data(user_id)
        user_servers = get_user_servers(user_id)
        wallet = get_wallet(user_id)
        
        msg = "👤 **حساب کاربری شما**"

🆔 **آیدی عددی:** `{user_id}`
📛 **نام:** {user_data.get('first_name', 'کاربر')}
👤 **یوزرنیم:** @{user_data.get('username', 'ندارد')}
📊 **تعداد سرورهای فعال:** {len(user_servers)}
📈 **سرورهای امروز:** {user_data.get('daily_count', 0)}/2
💰 **موجودی کیف پول:** {wallet} تومان
⚠️ **تعداد اخطارها:** {user_data.get('warnings', 0)}"""
        
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard("back_to_main"),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    if data == "my_wallet":
        wallet = get_wallet(user_id)
        msg = f"""💰 **کیف پول شما**

💵 **موجودی:** {wallet} تومان

📝 **هیچ تراکنشی وجود ندارد.**"""
        
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard("back_to_main"),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    if data == "help":
        help_text = """**راهنما و قوانین:**

**۱. دریافت سرور رایگان:**
- هر کاربر روزانه ۲ سرور دریافت میکنه
- حجم هر سرور: ۱ گیگابایت

**۲. سرویس‌های من:**
- مشاهده لیست سرورهای دریافت شده
- دریافت QR Code
- مشاهده مشخصات سرور
- دریافت کانفیگ

**۳. حساب کاربری:**
- مشاهده آیدی عددی
- مشاهده نام و یوزرنیم
- تعداد سرورهای فعال

**۴. کیف پول:**
- مشاهده موجودی
- تاریخچه تراکنش‌ها"""
        
        await callback.message.edit_text(
            help_text,
            reply_markup=get_back_keyboard("back_to_main"),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    if data == "admin_panel" and int(user_id) == OWNER_ID:
        await callback.message.edit_text(
            "🔧 **پنل مدیریت**\n\nلطفاً یکی از گزینه‌های زیر رو انتخاب کنید:",
            reply_markup=get_admin_keyboard()
        )
        await callback.answer()
        return
    
    if data.startswith("qr_"):
        await callback.answer("📱 QR Code در حال تولید...", show_alert=True)
        return
    
    if data.startswith("info_"):
        await callback.answer("📋 مشخصات سرور...", show_alert=True)
        return
    
    if data.startswith("config_"):
        await callback.answer("📄 کانفیگ سرور...", show_alert=True)
        return
    
    if data.startswith("ping_"):
        await callback.answer("📊 پینگ سرور...", show_alert=True)
        return
    
    if data.startswith("report_"):
        await callback.answer("⚠️ گزارش خرابی ثبت شد!", show_alert=True)
        return
    
    if data.startswith("delete_"):
        await callback.answer("🗑 سرویس حذف شد!", show_alert=True)
        return
    
    if data.startswith("rename_"):
        await callback.answer("✏️ تغییر نام سرور...", show_alert=True)
        return
    
    await callback.answer()
# ============================================
# بخش ۵: اجرا و مدیریت
# ============================================

# ==================== مدیریت اخطار ====================
@dp.message_handler(commands=['admin'])
async def admin_command(message: types.Message):
    if message.from_user.id == OWNER_ID:
        await message.answer(
            "🔧 **پنل مدیریت**",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer("❌ شما دسترسی به این بخش ندارید!")

# ==================== مدیریت کاربران ====================
@dp.message_handler(commands=['users'])
async def users_command(message: types.Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ شما دسترسی به این بخش ندارید!")
        return
    
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT user_id, first_name, username, joined_at FROM users")
        users = c.fetchall()
    finally:
        conn.close()
    
    if not users:
        await message.answer("📭 **هیچ کاربری ثبت نشده!**")
        return
    
    text = "📋 **لیست کاربران:**\n\n"
    for uid, first_name, username, joined_at in users:
        text += f"🆔 `{uid}` - {first_name or 'بدون نام'} (@{username or 'بدون یوزر'})\n"
    
    await message.answer(text, parse_mode="HTML")

# ==================== مدیریت سرورها ====================
@dp.message_handler(commands=['servers'])
async def servers_command(message: types.Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ شما دسترسی به این بخش ندارید!")
        return
    
    total = len(get_free_servers())
    await message.answer(f"📊 **تعداد سرورهای آزاد:** {total}")

# ==================== اجرا ====================
if __name__ == "__main__":
    print("=" * 50)
    print("🤖 ربات با Aiogram 2.x روشن شد!")
    print(f"👤 مالک: {OWNER_ID}")
    print("=" * 50)
    
    executor.start_polling(dp, skip_updates=True)
