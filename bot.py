# bot.py - کد کامل با Aiogram و کاستوم ایموجی روی دکمه‌ها
import asyncio
import logging
import sqlite3
import json
import random
import re
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, MessageEntity
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message
import pytz

# ==================== تنظیمات اولیه ====================
BOT_TOKEN = "8319089742:AAFoU3TT1hmpdiqd70fidyahUS9RG7CpVg4"
OWNER_ID = 7323216202
BOT_USERNAME = "@DEMONFREECONF_BOT"
PING_THRESHOLD = 130
PING_INTERVAL = 60

# تنظیم منطقه زمانی ایران
IRAN_TZ = pytz.timezone('Asia/Tehran')

# کاستوم ایموجی‌های دکمه‌ها
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

# راه‌اندازی
logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# ==================== دیتابیس ====================
def init_db():
    db = sqlite3.connect("bot.db", check_same_thread=False)
    cursor = db.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages(
        name TEXT PRIMARY KEY,
        text TEXT
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

# ==================== توابع دیتابیس ====================

def get_iran_time():
    return datetime.now(IRAN_TZ)

def format_iran_time(dt):
    return dt.strftime('%Y-%m-%d %H:%M')

def get_iran_time_iso():
    return get_iran_time().isoformat()

def get_all_users():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT user_id, daily_count, servers, first_name, username, joined_at, wallet, warnings, is_banned FROM users")
        return c.fetchall()
    finally:
        conn.close()

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
            conn2 = sqlite3.connect("bot.db", check_same_thread=False)
            c2 = conn2.cursor()
            try:
                c2.execute("UPDATE users SET daily_count=0, last_reset=? WHERE user_id=?",
                           (get_iran_time().isoformat(), str(user_id)))
                conn2.commit()
            finally:
                conn2.close()
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

def update_user_data(user_id, daily_count=None, servers=None, last_emoji_msg_id=None, wallet=None, warnings=None, is_banned=None):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        if daily_count is not None:
            c.execute("UPDATE users SET daily_count=? WHERE user_id=?", (daily_count, str(user_id)))
        if servers is not None:
            c.execute("UPDATE users SET servers=? WHERE user_id=?", (json.dumps(servers), str(user_id)))
        if last_emoji_msg_id is not None:
            c.execute("UPDATE users SET last_emoji_msg_id=? WHERE user_id=?", (last_emoji_msg_id, str(user_id)))
        if wallet is not None:
            c.execute("UPDATE users SET wallet=? WHERE user_id=?", (wallet, str(user_id)))
        if warnings is not None:
            c.execute("UPDATE users SET warnings=? WHERE user_id=?", (warnings, str(user_id)))
        if is_banned is not None:
            c.execute("UPDATE users SET is_banned=? WHERE user_id=?", (is_banned, str(user_id)))
        conn.commit()
    finally:
        conn.close()

def update_user_info(user_id, first_name, username):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("UPDATE users SET first_name=?, username=? WHERE user_id=?", (first_name, username, str(user_id)))
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

def deduct_wallet(user_id, amount):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        current = get_wallet(user_id)
        if current < amount:
            return False
        c.execute("UPDATE users SET wallet = wallet - ? WHERE user_id=?", (amount, str(user_id)))
        conn.commit()
        return True
    finally:
        conn.close()

def add_transaction(user_id, amount, trans_type, description):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("""
        INSERT INTO wallet_transactions(user_id, amount, type, description, created_at)
        VALUES(?,?,?,?,?)
        """, (str(user_id), amount, trans_type, description, get_iran_time().isoformat()))
        conn.commit()
    finally:
        conn.close()

def get_transactions(user_id, limit=10):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("""
        SELECT amount, type, description, created_at 
        FROM wallet_transactions 
        WHERE user_id=? 
        ORDER BY id DESC 
        LIMIT ?
        """, (str(user_id), limit))
        return c.fetchall()
    finally:
        conn.close()

def add_warning(user_id):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT warnings FROM users WHERE user_id=?", (str(user_id),))
        data = c.fetchone()
        warnings = (data[0] if data else 0) + 1
        
        if warnings >= 3:
            c.execute("UPDATE users SET warnings=?, is_banned=1 WHERE user_id=?", (warnings, str(user_id)))
            conn.commit()
            return True, warnings, True
        else:
            c.execute("UPDATE users SET warnings=? WHERE user_id=?", (warnings, str(user_id)))
            conn.commit()
            return True, warnings, False
    finally:
        conn.close()

def is_user_banned(user_id):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT is_banned FROM users WHERE user_id=?", (str(user_id),))
        data = c.fetchone()
        return data[0] == 1 if data else False
    finally:
        conn.close()

def get_warnings(user_id):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT warnings FROM users WHERE user_id=?", (str(user_id),))
        data = c.fetchone()
        return data[0] if data else 0
    finally:
        conn.close()

def add_server(config, ip="Unknown", port="Unknown", protocol="vless"):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO servers(config, ip, port, protocol, used_by, expiry, ping, last_ping_check, last_ping_notification) VALUES(?,?,?,?,?,?,?,?,?)",
                  (config, ip, port, protocol, None, None, 0, None, None))
        conn.commit()
        return c.lastrowid
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

def get_server_by_id(server_id):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM servers WHERE id=?", (server_id,))
        return c.fetchone()
    finally:
        conn.close()

def assign_server_to_user(server_id, user_id):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("UPDATE servers SET used_by=?, expiry=? WHERE id=?", (str(user_id), None, server_id))
        conn.commit()
    finally:
        conn.close()

def remove_server(server_id):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("DELETE FROM servers WHERE id=?", (server_id,))
        conn.commit()
    finally:
        conn.close()

def update_server_ping(server_id, ping):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("UPDATE servers SET ping=?, last_ping_check=? WHERE id=?", (ping, get_iran_time().isoformat(), server_id))
        conn.commit()
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

def get_total_servers():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) FROM servers")
        return c.fetchone()[0]
    finally:
        conn.close()

def get_free_servers_count():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) FROM servers WHERE used_by IS NULL")
        return c.fetchone()[0]
    finally:
        conn.close()

def get_used_servers_count():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) FROM servers WHERE used_by IS NOT NULL")
        return c.fetchone()[0]
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

def get_message(name):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT text FROM messages WHERE name=?", (name,))
        data = c.fetchone()
        return data[0] if data else None
    finally:
        conn.close()

def save_ping_report(server_id, user_id, ping):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO ping_reports(server_id, user_id, ping, reported_at) VALUES(?,?,?,?)",
                  (server_id, str(user_id), ping, get_iran_time().isoformat()))
        conn.commit()
    finally:
        conn.close()

def save_server_report(server_id, user_id, report_text):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO server_reports(server_id, user_id, report_text, reported_at) VALUES(?,?,?,?)",
                  (server_id, str(user_id), report_text, get_iran_time().isoformat()))
        conn.commit()
    finally:
        conn.close()

def get_pending_ping_reports():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM ping_reports WHERE status='pending'")
        return c.fetchall()
    finally:
        conn.close()

def update_ping_report_status(report_id, status):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("UPDATE ping_reports SET status=? WHERE id=?", (status, report_id))
        conn.commit()
    finally:
        conn.close()

def get_pending_server_reports():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM server_reports WHERE status='pending'")
        return c.fetchall()
    finally:
        conn.close()

def update_server_report_status(report_id, status):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("UPDATE server_reports SET status=? WHERE id=?", (status, report_id))
        conn.commit()
    finally:
        conn.close()

def get_required_channels():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT value FROM bot_settings WHERE key='required_channels'")
        data = c.fetchone()
        if data and data[0]:
            try:
                return json.loads(data[0])
            except:
                return eval(data[0])
        return []
    finally:
        conn.close()

def set_required_channels(channels_list):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO bot_settings(key, value) VALUES(?,?)", 
                  ("required_channels", json.dumps(channels_list)))
        conn.commit()
    finally:
        conn.close()

def check_user_in_channel(user_id, channel_username):
    try:
        member = bot.get_chat_member(f"@{channel_username}", user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except:
        pass
    return False

def check_all_channels(user_id):
    channels = get_required_channels()
    if not channels:
        return True, []
    
    not_member = []
    for channel in channels:
        if not check_user_in_channel(user_id, channel):
            not_member.append(channel)
    
    return len(not_member) == 0, not_member

# ==================== توابع کمکی ====================

def get_welcome_emoji():
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("SELECT value FROM bot_settings WHERE key='welcome_emoji'")
        data = c.fetchone()
        return data[0] if data and data[0] else "5900199258316869673"
    finally:
        conn.close()

def set_welcome_emoji(emoji_id):
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO bot_settings(key, value) VALUES(?,?)", 
                  ("welcome_emoji", emoji_id))
        conn.commit()
    finally:
        conn.close()

def create_custom_emoji_button(text, callback_data, emoji_id):
    """ساخت دکمه با کاستوم ایموجی"""
    return InlineKeyboardButton(
        text=text,
        callback_data=callback_data,
        icon_custom_emoji_id=emoji_id
    )

def create_emoji_button(text, callback_data, emoji_id=None):
    """ساخت دکمه با ایموجی معمولی یا کاستوم"""
    if emoji_id:
        return InlineKeyboardButton(
            text=text,
            callback_data=callback_data,
            icon_custom_emoji_id=emoji_id
        )
    return InlineKeyboardButton(text=text, callback_data=callback_data)

def get_server_name(user_id):
    return f"{user_id}_{BOT_USERNAME}_1GB"

def get_server_emoji(server_id):
    return EMOJI_QR

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

# ==================== کیبوردها با کاستوم ایموجی ====================

def get_main_keyboard(user_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            create_custom_emoji_button("📥 دریافت سرور", "get_free_server", EMOJI_GET_SERVER),
            create_custom_emoji_button("📋 سرویس‌های من", "my_services", EMOJI_MY_SERVICES)
        ],
        [
            create_custom_emoji_button("👤 حساب کاربری", "my_account", EMOJI_MY_ACCOUNT),
            create_custom_emoji_button("💰 کیف پول", "my_wallet", EMOJI_MY_WALLET)
        ],
        [
            create_custom_emoji_button("ℹ️ راهنما", "help", EMOJI_HELP)
        ]
    ])
    
    if int(user_id) == OWNER_ID:
        keyboard.inline_keyboard.append([
            create_custom_emoji_button("🔧 پنل مدیریت", "admin_panel", EMOJI_ADMIN)
        ])
    
    return keyboard

def get_server_action_keyboard(server_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            create_custom_emoji_button("📱 QR Code", f"qr_{server_id}", EMOJI_QR),
            create_custom_emoji_button("📋 مشخصات", f"info_{server_id}", EMOJI_INFO)
        ],
        [
            create_custom_emoji_button("📄 کانفیگ", f"config_{server_id}", EMOJI_CONFIG),
            create_custom_emoji_button("📊 پینگ", f"ping_{server_id}", EMOJI_PING)
        ],
        [
            create_custom_emoji_button("⚠️ گزارش خرابی", f"report_{server_id}", EMOJI_REPORT),
            create_custom_emoji_button("🗑 حذف سرویس", f"delete_{server_id}", EMOJI_DELETE)
        ],
        [
            create_custom_emoji_button("✏️ تغییر نام", f"rename_{server_id}", EMOJI_RENAME),
            create_custom_emoji_button("🔙 بازگشت", "back_to_services", EMOJI_BACK)
        ]
    ])
    return keyboard

def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("📊 آمار", callback_data="admin_stats"),
            InlineKeyboardButton("➕ اضافه کردن", callback_data="admin_add_servers")
        ],
        [
            InlineKeyboardButton("🗑 حذف سرور", callback_data="admin_remove_server"),
            InlineKeyboardButton("📋 کاربران", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton("✏️ ویرایش پیام‌ها", callback_data="admin_edit_messages"),
            InlineKeyboardButton("📊 پینگ بالا", callback_data="admin_ping_reports")
        ],
        [
            InlineKeyboardButton("⚠️ گزارش خرابی", callback_data="admin_server_reports"),
            InlineKeyboardButton("🔄 آپدیت سرویس", callback_data="admin_update_service")
        ],
        [
            InlineKeyboardButton("📢 چنل‌های اجباری", callback_data="admin_required_channels"),
            InlineKeyboardButton("💰 مدیریت کیف پول", callback_data="admin_wallet")
        ],
        [
            InlineKeyboardButton("⚠️ مدیریت اخطارها", callback_data="admin_warnings"),
            InlineKeyboardButton("✏️ تنظیم ایموجی", callback_data="admin_set_emoji")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
        ]
    ])
    return keyboard

def get_back_keyboard(callback):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [create_custom_emoji_button("🔙 بازگشت", callback, EMOJI_BACK)]
    ])
    return keyboard

def get_channel_management_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("➕ افزودن چنل جدید", callback_data="add_required_channel")],
        [InlineKeyboardButton("📋 لیست چنل‌ها", callback_data="list_required_channels")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
    ])
    return keyboard

# ==================== پیام‌های پیش‌فرض ====================

DEFAULT_MESSAGES = {
    "welcome": """
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
""",
    
    "help": """
**راهنما و قوانین:**

**۱. دریافت سرور رایگان:**
- هر کاربر روزانه ۲ سرور دریافت میکنه
- حجم هر سرور: ۱ گیگابایت
- مدت زمان: نامحدود

**۲. سرویس‌های من:**
- مشاهده لیست سرورهای دریافت شده
- دریافت QR Code
- مشاهده مشخصات سرور
- دریافت کانفیگ (کپی با یک کلیک)
- مشاهده پینگ سرور
- گزارش خرابی سرویس
- حذف سرویس
- تغییر نام سرور

**۳. کیف پول:**
- مشاهده موجودی
- تاریخچه تراکنش‌ها

**۴. نکات مهم:**
- سرورها کاملاً رایگان هستن
- مدت زمان سرورها نامحدوده

در صورت مشکل با پشتیبانی تماس بگیرید.
""",
    
    "server_building": """
⏳ **سرور رایگان شما در حال ساخته شدن هست...**
لطفاً چند لحظه صبر کنید.
""",
    
    "server_created": """
✅ **سرویس شما با موفقیت ایجاد شد!**

📌 **نام سرور:** {server_name}

می‌تونید از بخش **سرویس‌های من**، سرویس خود رو مشاهده کنید.
""",
    
    "no_free_servers": """
❌ **مشکل در ارتباط با پنل!**

متأسفانه در حال حاضر هیچ سرور آزادی موجود نیست.
لطفاً بعداً دوباره تلاش کنید.
""",
    
    "daily_limit": """
⚠️ **شما امروز ۲ سرور رایگان دریافت کردید!**

هر روز فقط ۲ سرور می‌تونید دریافت کنید.
از فردا دوباره تلاش کنید.
""",
    
    "no_services": """
📭 **شما هیچ سرویسی دریافت نکردید!**

از بخش **"دریافت سرور"** اقدام کنید.
""",
    
    "server_info": """
📋 **مشخصات سرور**

🔹 **نام کانفیگ:** {name}
🔹 **پروتکل:** {protocol}
🔹 **IP:** {ip}
🔹 **پورت:** {port}
🔹 **لوکیشن:** {location}
🔹 **حجم:** {volume}
🔹 **مدت زمان:** نامحدود
🔹 **زمان دریافت:** {received}
🔹 **وضعیت:** {status}
""",
    
    "rename_prompt": """
✏️ **لطفاً نام جدید سرور رو وارد کنید:**

(برای انصراف /cancel رو بفرستید)
""",
    
    "rename_confirmed": """
✅ **نام سرور با موفقیت به '{new_name}' تغییر کرد!**

📌 می‌تونید کانفیگ جدید رو از بخش دریافت کانفیگ بگیرید.
""",
    
    "my_account": """
👤 **حساب کاربری شما**

🆔 **آیدی عددی:** `{user_id}`
📛 **نام:** {first_name}
👤 **یوزرنیم:** {username}
📊 **تعداد سرورهای فعال:** {active_servers}
📋 **کل سرورهای دریافت شده:** {total_servers}
⏰ **تاریخ عضویت:** {joined_at}
📈 **سرورهای امروز:** {today_count}/2
💰 **موجودی کیف پول:** {wallet} تومان
⚠️ **تعداد اخطارها:** {warnings}

برای مشاهده سرورها به بخش سرویس‌های من برید.
""",
    
    "my_wallet": """
💰 **کیف پول شما**

💵 **موجودی:** {balance} تومان

**تاریخچه تراکنش‌ها:**
{transactions}
""",
    
    "ping_result": """
📊 **پینگ سرور {server_name}**

🔄 **وضعیت:** {status}
📶 **پینگ:** {ping} ms

{status_emoji} **توضیح:**
{description}

اگر پینگ بالاست می‌تونید از دکمه **گزارش خرابی** استفاده کنید.
""",
    
    "report_prompt": """
⚠️ **گزارش خرابی سرویس**

لطفاً مشکل خود را توضیح دهید:

**مثال:**
- سرور وصل نمیشه
- سرعت بسیار پایین است
- قطع و وصل مکرر

(برای انصراف /cancel رو بفرستید)
""",
    
    "report_sent": """
✅ **گزارش شما با موفقیت ارسال شد!**

📌 **سرور:** {server_name}
📝 **گزارش:** {report_text}

مدیریت در اسرع وقت بررسی خواهد کرد.
""",
    
    "delete_confirmation": """
⚠️ **آیا از حذف سرویس '{server_name}' مطمئن هستید؟**

پس از حذف، این سرویس قابل بازیابی نیست.
""",
    
    "delete_success": """
✅ **سرویس '{server_name}' با موفقیت حذف شد!**
""",
    
    "qr_code_sent": """
📱 **QR Code سرور {server_name}**

QR Code سرویس شما در زیر ارسال شده است:
""",
    
    "config_sent": """
📄 **کانفیگ سرور {server_name}**

🔗 **لوکیشن:** {location}

💡 **برای کپی کردن، روی متن کانفیگ کلیک کنید:**

`{config}`
""",
    
    "server_updated_notification": """
🔄 **سرویس شما آپدیت شده!**

📌 **نام سرور:** {server_name}

🔗 **لطفاً برای دریافت لینک جدید به بخش سرویس‌های من بروید.**

از بخش سرویس‌های من می‌تونید کانفیگ جدید رو دریافت کنید.
""",
    
    "required_channels_check": """
📢 **عضویت در چنل اجباری**

برای استفاده از ربات باید عضو چنل‌های زیر باشید:

{channels}

پس از عضویت روی دکمه **"تأیید عضویت"** کلیک کنید.
""",
    
    "required_channels_ok": """
✅ **عضویت شما تأیید شد!**

به ربات خوش آمدید.
می‌تونید از تمام قابلیت‌های ربات استفاده کنید.

لطفاً یکی از گزینه‌های زیر رو انتخاب کنید:
""",
    
    "required_channels_fail": """
❌ **شما عضو همه چنل‌های اجباری نیستید!**

لطفاً ابتدا عضو شوید سپس روی **"تأیید عضویت"** کلیک کنید.

{channels}

پس از عضویت روی دکمه تأیید کلیک کنید.
""",
    
    "admin_panel": """
🔧 **پنل مدیریت**

لطفاً یکی از گزینه‌های زیر رو انتخاب کنید:
""",
    
    "admin_stats": """
📊 **آمار کلی:**

🔹 **تعداد کل سرورها:** {total}
🔹 **سرورهای آزاد:** {free}
🔹 **سرورهای در حال استفاده:** {used}
🔹 **تعداد کل کاربران:** {users}

📌 **جزئیات سرورها:**
{details}
""",
    
    "admin_add_prompt": """
📝 **لطفاً کانفیگ‌های سرور رو به صورت عمده وارد کنید:**

⚠️ **هر کانفیگ در یک خط جداگانه**

**مثال:**
`vless://example@server1.com:443?...`
`vless://example@server2.com:443?...`

برای لغو /cancel رو بفرستید
""",
    
    "admin_add_success": """
✅ **{count} سرور با موفقیت به مخزن اضافه شد!**

📊 **تعداد کل سرورها:** {total}
🆔 **محدوده آی‌دی:** {id_range}

💡 برای مشاهده سرورها به بخش آمار برید.
""",
    
    "admin_users_list": """
📋 **لیست کاربران:**

{users}
""",
    
    "admin_remove_prompt": """
🗑 **لطفاً سروری که می‌خواید حذف کنید رو انتخاب کنید:**
""",
    
    "admin_remove_success": """
✅ **سرور با آی‌دی {id} با موفقیت حذف شد!**
""",
    
    "admin_edit_messages": """
✏️ **ویرایش پیام‌ها**

لطفاً بخش مورد نظر رو انتخاب کنید:

**📌 بخش‌های قابل ویرایش:**
• Welcome - خوش‌آمدگویی
• Help - راهنما
• Server Building - در حال ساخت
• Server Created - ساخته شد
• No Free Servers - بدون سرور
• Daily Limit - محدودیت روزانه
• No Services - بدون سرویس
• Server Info - مشخصات سرور
• Rename Prompt - تغییر نام
• Rename Confirmed - تایید تغییر
• My Account - حساب کاربری
• My Wallet - کیف پول
• Ping Result - نتیجه پینگ
• Report Prompt - گزارش خرابی
• Report Sent - ارسال گزارش
• Delete Confirmation - تأیید حذف
• Delete Success - حذف موفق
• QR Code Sent - ارسال QR
• Config Sent - ارسال کانفیگ
• Server Updated Notification - آپدیت
• Required Channels Check - چک
• Required Channels OK - تایید
• Required Channels Fail - خطا

**متغیرهای قابل استفاده:**
`{{user_id}}` - آیدی عددی کاربر
`{{username}}` - یوزرنیم کاربر
`{{first_name}}` - نام کاربر
`{{server_name}}` - نام سرور
`{{server_id}}` - آی‌دی سرور
`{{config}}` - کانفیگ سرور
`{{ping}}` - میزان پینگ
`{{volume}}` - حجم سرور
`{{duration}}` - مدت زمان
`{{status}}` - وضعیت
`{{received}}` - زمان دریافت
`{{expiry}}` - زمان انقضا
`{{time}}` - زمان فعلی
`{{location}}` - لوکیشن سرور
`{{ip}}` - IP سرور
`{{port}}` - پورت سرور
`{{protocol}}` - پروتکل
`{{new_name}}` - نام جدید
`{{balance}}` - موجودی کیف پول
`{{transactions}}` - تاریخچه تراکنش‌ها
`{{wallet}}` - موجودی کیف پول
`{{warnings}}` - تعداد اخطارها
`{{count}}` - تعداد
`{{details}}` - جزئیات

برای لغو /cancel رو بفرستید
""",
    
    "admin_edit_prompt": """
✏️ **لطفاً متن جدید رو ارسال کنید:**

**متغیرهای قابل استفاده:**
`{{user_id}}` - آیدی عددی کاربر
`{{username}}` - یوزرنیم کاربر
`{{first_name}}` - نام کاربر
`{{server_name}}` - نام سرور
`{{server_id}}` - آی‌دی سرور
`{{config}}` - کانفیگ سرور
`{{ping}}` - میزان پینگ
`{{volume}}` - حجم سرور
`{{duration}}` - مدت زمان
`{{status}}` - وضعیت
`{{received}}` - زمان دریافت
`{{expiry}}` - زمان انقضا
`{{time}}` - زمان فعلی
`{{location}}` - لوکیشن سرور
`{{ip}}` - IP سرور
`{{port}}` - پورت سرور
`{{protocol}}` - پروتکل
`{{new_name}}` - نام جدید
`{{balance}}` - موجودی کیف پول
`{{transactions}}` - تاریخچه تراکنش‌ها
`{{wallet}}` - موجودی کیف پول
`{{warnings}}` - تعداد اخطارها
`{{count}}` - تعداد
`{{details}}` - جزئیات

برای لغو /cancel رو بفرستید
""",
    
    "admin_edit_success": """
✅ **پیام با موفقیت ذخیره شد!**
""",
    
    "ping_reports_list": """
📊 **گزارش‌های پینگ بالا:**

{reports}
""",
    
    "update_service_prompt": """
🔄 **آپدیت سرویس**

لطفاً آی‌دی سرور و کانفیگ جدید رو به فرمت زیر ارسال کنید:

`سرور_آی‌دی|کانفیگ_جدید`

**مثال:**
`5|vless://example@new-server.com:443?...`

برای لغو /cancel رو بفرستید
""",
    
    "required_channels_prompt": """
📢 **تنظیم چنل‌های اجباری**

لطفاً یوزرنیم چنل‌های مورد نظر رو وارد کنید:

**نکات:**
- هر چنل در یک خط جداگانه
- بدون @ وارد کنید
- ربات باید ادمین چنل باشد
- حداکثر ۱۰ چنل

**مثال:**
`my_channel1`
`my_channel2`

برای لغو /cancel رو بفرستید
""",
    
    "required_channels_set": """
✅ **چنل‌های اجباری با موفقیت تنظیم شدند!**

📢 **چنل‌های فعلی:**
{channels}

از این پس کاربران برای استفاده از ربات باید عضو این چنل‌ها باشند.
""",
    
    "required_channels_list": """
📢 **لیست چنل‌های اجباری فعلی:**

{channels}

📊 **تعداد:** {count} چنل

برای حذف یک چنل، روی دکمه مربوطه کلیک کنید.
""",
    
    "required_channel_removed": """
✅ **چنل @{channel} با موفقیت حذف شد!**

لیست چنل‌های اجباری به‌روزرسانی شد.
""",
    
    "server_reports_list": """
⚠️ **گزارش‌های خرابی سرویس:**

{reports}
""",
    
    "server_report_resolved": """
✅ **گزارش با موفقیت بررسی شد!**

🆔 سرور: {server_id}
👤 کاربر: {user_id}

وضعیت: بررسی شده
""",
    
    "admin_report_notification": """
⚠️ **گزارش خرابی سرویس جدید!**

🆔 سرور: {server_id}
👤 کاربر: {user_id}
📝 گزارش: {report_text}
⏰ زمان: {time}

لطفاً بررسی کنید.
""",
    
    "admin_set_emoji_prompt": """
✏️ **تنظیم کاستوم ایموجی**

لطفاً کد ایموجی جدید رو وارد کنید:

**مثال:**
`5900199258316869673`

برای لغو /cancel رو بفرستید
""",
    
    "admin_set_emoji_success": """
✅ **کاستوم ایموجی با موفقیت تغییر کرد!**

🆔 **کد جدید:** {emoji_id}

از این پس این ایموجی برای دکمه‌ها استفاده خواهد شد.
""",
    
    "admin_wallet_prompt": """
💰 **مدیریت کیف پول**

لطفاً عملیات را انتخاب کنید:

`افزایش|آیدی_کاربر|مبلغ` یا `کاهش|آیدی_کاربر|مبلغ`

**مثال:**
`افزایش|7323216202|50000`

برای لغو /cancel رو بفرستید
""",
    
    "admin_wallet_success": """
✅ **عملیات با موفقیت انجام شد!**

👤 **کاربر:** {user_id}
💰 **موجودی جدید:** {balance} تومان
📝 **نوع:** {type}
💵 **مبلغ:** {amount} تومان
""",
    
    "admin_warnings_prompt": """
⚠️ **مدیریت اخطارها**

لطفاً عملیات را انتخاب کنید:

`افزایش|آیدی_کاربر` یا `حذف|آیدی_کاربر` یا `لیست`

**مثال:**
`افزایش|7323216202`

برای لغو /cancel رو بفرستید
""",
    
    "admin_warnings_list": """
⚠️ **لیست کاربران با اخطار:**

{users}
""",
    
    "admin_warnings_success": """
✅ **عملیات با موفقیت انجام شد!**

👤 **کاربر:** {user_id}
⚠️ **تعداد اخطارها:** {warnings}
📝 **وضعیت:** {status}
""",
    
    "admin_warnings_cleared": """
✅ **تمام اخطارهای کاربر پاک شد!**

👤 **کاربر:** {user_id}
⚠️ **تعداد اخطارها:** ۰
📝 **وضعیت:** عادی
"""
}

# ==================== هندلرها ====================

class EditMessageState(StatesGroup):
    waiting_for_text = State()
    waiting_for_emoji = State()
    waiting_for_config = State()
    waiting_for_channel = State()
    waiting_for_wallet = State()
    waiting_for_warnings = State()
    waiting_for_update = State()
    waiting_for_rename = State()
    waiting_for_report = State()

@dp.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or ""
    username = message.from_user.username or ""
    update_user_info(user_id, first_name, username)
    
    if is_user_banned(user_id):
        await message.answer("🚫 **شما به دلیل تخلف از قوانین مسدود شده‌اید!**\nبرای رفع مسدودیت با پشتیبانی تماس بگیرید.", parse_mode="HTML")
        return
    
    channels = get_required_channels()
    if channels and int(user_id) != OWNER_ID:
        is_member, not_member = check_all_channels(user_id)
        if not is_member:
            channels_text = "\n".join([f"• @{ch}" for ch in not_member])
            msg = get_message("required_channels_check") or DEFAULT_MESSAGES["required_channels_check"]
            msg = msg.format(channels=channels_text)
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("✅ تأیید عضویت", callback_data="check_membership")],
                [InlineKeyboardButton("📢 عضویت در چنل", url=f"https://t.me/{not_member[0]}")]
            ])
            
            await message.answer(msg, reply_markup=keyboard, parse_mode="HTML")
            return
    
    welcome_text = get_message("welcome") or DEFAULT_MESSAGES["welcome"]
    welcome_text = welcome_text.format(first_name=first_name)
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(user_id),
        parse_mode="HTML"
    )

# ==================== ادامه هندلرها در بخش بعدی ====================
# ==================== ادامه هندلرها ====================

@dp.callback_query()
async def handle_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = callback.data
    
    if int(user_id) != OWNER_ID and is_user_banned(user_id):
        await callback.answer("🚫 شما مسدود هستید!", show_alert=True)
        return
    
    if int(user_id) != OWNER_ID:
        channels = get_required_channels()
        if channels:
            is_member, not_member = check_all_channels(user_id)
            if not is_member and data not in ["check_membership", "back_to_main"]:
                channels_text = "\n".join([f"• @{ch}" for ch in not_member])
                msg = get_message("required_channels_check") or DEFAULT_MESSAGES["required_channels_check"]
                msg = msg.format(channels=channels_text)
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton("✅ تأیید عضویت", callback_data="check_membership")],
                    [InlineKeyboardButton("📢 عضویت در چنل", url=f"https://t.me/{not_member[0]}")]
                ])
                
                await callback.message.edit_text(msg, reply_markup=keyboard, parse_mode="HTML")
                await callback.answer()
                return
    
    if data == "check_membership":
        channels = get_required_channels()
        if not channels:
            await callback.answer("✅ هیچ چنل اجباری تنظیم نشده!", show_alert=True)
            return
        
        is_member, not_member = check_all_channels(user_id)
        if is_member:
            msg = get_message("required_channels_ok") or DEFAULT_MESSAGES["required_channels_ok"]
            await callback.message.edit_text(
                msg,
                reply_markup=get_main_keyboard(user_id),
                parse_mode="HTML"
            )
            await callback.answer("✅ عضویت تأیید شد!", show_alert=True)
        else:
            channels_text = "\n".join([f"• @{ch}" for ch in not_member])
            msg = get_message("required_channels_fail") or DEFAULT_MESSAGES["required_channels_fail"]
            msg = msg.format(channels=channels_text)
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton("✅ تأیید عضویت", callback_data="check_membership")],
                [InlineKeyboardButton("📢 عضویت در چنل", url=f"https://t.me/{not_member[0]}")]
            ])
            
            await callback.message.edit_text(msg, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer("❌ عضو همه چنل‌ها نیستید!", show_alert=True)
        return
    
    if data == "back_to_main":
        user_data = get_user_data(user_id)
        first_name = user_data.get("first_name", "")
        
        welcome_text = get_message("welcome") or DEFAULT_MESSAGES["welcome"]
        welcome_text = welcome_text.format(first_name=first_name)
        
        await callback.message.edit_text(
            welcome_text,
            reply_markup=get_main_keyboard(user_id),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    if data == "get_free_server":
        user_data = get_user_data(user_id)
        
        if user_data["daily_count"] >= 2:
            msg = get_message("daily_limit") or DEFAULT_MESSAGES["daily_limit"]
            await callback.message.edit_text(msg, reply_markup=get_back_keyboard("back_to_main"), parse_mode="HTML")
            await callback.answer()
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [create_custom_emoji_button("🟣 V2Ray", "vpn_v2ray", EMOJI_GET_SERVER)],
            [create_custom_emoji_button("🔙 بازگشت", "back_to_main", EMOJI_BACK)]
        ])
        
        await callback.message.edit_text("🔍 انتخاب نوع سرور:", reply_markup=keyboard)
        await callback.answer()
        return
    
    if data == "vpn_v2ray":
        free_servers = get_free_servers()
        
        if not free_servers:
            msg = get_message("no_free_servers") or DEFAULT_MESSAGES["no_free_servers"]
            await callback.message.edit_text(msg, reply_markup=get_back_keyboard("back_to_main"), parse_mode="HTML")
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
        
        user_data = get_user_data(user_id)
        update_user_data(user_id, user_data["daily_count"] + 1)
        
        building_msg = get_message("server_building") or DEFAULT_MESSAGES["server_building"]
        await callback.message.edit_text(building_msg, parse_mode="HTML")
        
        await asyncio.sleep(5)
        
        created_msg = get_message("server_created") or DEFAULT_MESSAGES["server_created"]
        created_msg = created_msg.format(server_name=server_name)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                create_custom_emoji_button("📋 سرویس‌های من", "my_services", EMOJI_MY_SERVICES),
                create_custom_emoji_button("🔙 بازگشت", "back_to_main", EMOJI_BACK)
            ]
        ])
        
        await callback.message.edit_text(
            created_msg,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    if data == "my_services":
        user_servers = get_user_servers(user_id)
        
        if not user_servers:
            msg = get_message("no_services") or DEFAULT_MESSAGES["no_services"]
            await callback.message.edit_text(msg, reply_markup=get_back_keyboard("back_to_main"), parse_mode="HTML")
            await callback.answer()
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for server in user_servers:
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    f"📌 {server['name']} - ✅ فعال",
                    callback_data=f"view_server_{server['server_id']}"
                )
            ])
        keyboard.inline_keyboard.append([
            create_custom_emoji_button("🔙 بازگشت", "back_to_main", EMOJI_BACK)
        ])
        
        await callback.message.edit_text("📋 لیست سرویس‌های شما:", reply_markup=keyboard)
        await callback.answer()
        return
    
    if data.startswith("view_server_"):
        server_id = int(data.split("_")[2])
        user_servers = get_user_servers(user_id)
        server = next((s for s in user_servers if s["server_id"] == server_id), None)
        
        if not server:
            await callback.message.edit_text("❌ سرور مورد نظر یافت نشد!", reply_markup=get_back_keyboard("back_to_main"))
            await callback.answer()
            return
        
        cursor.execute("SELECT ping FROM servers WHERE id=?", (server_id,))
        ping_data = cursor.fetchone()
        ping = ping_data[0] if ping_data and ping_data[0] else 0
        
        status = "✅ فعال"
        if ping > PING_THRESHOLD and ping > 0:
            status = f"⚠️ پینگ بالا ({ping}ms)"
        
        await callback.message.edit_text(
            f"📌 سرور: {server['name']}\n⏳ وضعیت: {status}\n📊 حجم: {server['volume']}",
            reply_markup=get_server_action_keyboard(server_id)
        )
        await callback.answer()
        return
    
    if data == "back_to_services":
        user_servers = get_user_servers(user_id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for server in user_servers:
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    f"📌 {server['name']} - ✅ فعال",
                    callback_data=f"view_server_{server['server_id']}"
                )
            ])
        keyboard.inline_keyboard.append([
            create_custom_emoji_button("🔙 بازگشت", "back_to_main", EMOJI_BACK)
        ])
        
        await callback.message.edit_text("📋 لیست سرویس‌های شما:", reply_markup=keyboard)
        await callback.answer()
        return
    
    if data.startswith("qr_"):
        server_id = int(data.split("_")[1])
        user_servers = get_user_servers(user_id)
        server = next((s for s in user_servers if s["server_id"] == server_id), None)
        
        if not server:
            await callback.answer("❌ سرور یافت نشد!", show_alert=True)
            return
        
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(server["config"])
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            bio = BytesIO()
            img.save(bio, 'PNG')
            bio.seek(0)
            
            msg = get_message("qr_code_sent") or DEFAULT_MESSAGES["qr_code_sent"]
            msg = msg.format(server_name=server['name'])
            
            await callback.message.delete()
            await callback.message.answer(msg, parse_mode="HTML")
            await callback.message.answer_photo(
                types.BufferedInputFile(bio.getvalue(), filename="qr.png"),
                caption=f"📱 QR Code سرور {server['name']}",
                reply_markup=get_back_keyboard(f"view_server_{server_id}")
            )
        except Exception as e:
            await callback.answer("❌ خطا در تولید QR Code!", show_alert=True)
        await callback.answer()
        return
    
    if data.startswith("info_"):
        server_id = int(data.split("_")[1])
        user_servers = get_user_servers(user_id)
        server = next((s for s in user_servers if s["server_id"] == server_id), None)
        
        if not server:
            await callback.answer("❌ سرور یافت نشد!", show_alert=True)
            return
        
        try:
            received = datetime.fromisoformat(server["received_at"])
        except:
            received = get_iran_time()
        
        cursor.execute("SELECT ping FROM servers WHERE id=?", (server_id,))
        ping_data = cursor.fetchone()
        ping = ping_data[0] if ping_data and ping_data[0] else 0
        
        status = "✅ فعال"
        if ping > PING_THRESHOLD and ping > 0:
            status = f"⚠️ پینگ بالا ({ping}ms)"
        
        ip = server['ip']
        location = get_location_from_ip(ip)
        
        msg = get_message("server_info") or DEFAULT_MESSAGES["server_info"]
        msg = msg.format(
            name=server['name'],
            protocol=server['protocol'],
            ip=ip,
            port=server['port'],
            location=location,
            volume=server['volume'],
            received=format_iran_time(received),
            status=status
        )
        
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard(f"view_server_{server_id}"),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    if data.startswith("config_"):
        server_id = int(data.split("_")[1])
        user_servers = get_user_servers(user_id)
        server = next((s for s in user_servers if s["server_id"] == server_id), None)
        
        if not server:
            await callback.answer("❌ سرور یافت نشد!", show_alert=True)
            return
        
        ip = server['ip']
        location = get_location_from_ip(ip)
        
        msg = get_message("config_sent") or DEFAULT_MESSAGES["config_sent"]
        msg = msg.format(
            server_name=server['name'],
            location=location,
            config=server['config']
        )
        
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard(f"view_server_{server_id}"),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    if data.startswith("ping_"):
        server_id = int(data.split("_")[1])
        user_servers = get_user_servers(user_id)
        server = next((s for s in user_servers if s["server_id"] == server_id), None)
        
        if not server:
            await callback.answer("❌ سرور یافت نشد!", show_alert=True)
            return
        
        cursor.execute("SELECT ping FROM servers WHERE id=?", (server_id,))
        ping_data = cursor.fetchone()
        ping = ping_data[0] if ping_data and ping_data[0] else 0
        
        if ping == 0:
            status = "❌ نامشخص"
            status_emoji = "❓"
            description = "پینگ قابل اندازه‌گیری نیست"
        elif ping < 50:
            status = "✅ عالی"
            status_emoji = "🌟"
            description = "پینگ بسیار خوب - اتصال پایدار"
        elif ping < 100:
            status = "✅ خوب"
            status_emoji = "👍"
            description = "پینگ مناسب - اتصال قابل قبول"
        elif ping < PING_THRESHOLD:
            status = "⚠️ متوسط"
            status_emoji = "⚠️"
            description = "پینگ نسبتاً بالا - ممکنه کمی کند باشه"
        else:
            status = "❌ ضعیف"
            status_emoji = "🚫"
            description = "پینگ بسیار بالا - نیاز به بررسی دارد"
        
        msg = get_message("ping_result") or DEFAULT_MESSAGES["ping_result"]
        msg = msg.format(
            server_name=server['name'],
            status=status,
            ping=ping,
            status_emoji=status_emoji,
            description=description
        )
        
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard(f"view_server_{server_id}"),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    if data.startswith("report_"):
        server_id = int(data.split("_")[1])
        await state.update_data(report_server_id=server_id)
        
        msg = get_message("report_prompt") or DEFAULT_MESSAGES["report_prompt"]
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard(f"view_server_{server_id}"),
            parse_mode="HTML"
        )
        await state.set_state(EditMessageState.waiting_for_report)
        await callback.answer()
        return
    
    if data.startswith("delete_"):
        server_id = int(data.split("_")[1])
        user_servers = get_user_servers(user_id)
        server = next((s for s in user_servers if s["server_id"] == server_id), None)
        
        if not server:
            await callback.answer("❌ سرور یافت نشد!", show_alert=True)
            return
        
        msg = get_message("delete_confirmation") or DEFAULT_MESSAGES["delete_confirmation"]
        msg = msg.format(server_name=server['name'])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"confirm_delete_{server_id}"),
                InlineKeyboardButton("❌ انصراف", callback_data=f"view_server_{server_id}")
            ]
        ])
        
        await callback.message.edit_text(msg, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return
    
    if data.startswith("confirm_delete_"):
        server_id = int(data.split("_")[2])
        user_servers = get_user_servers(user_id)
        server = next((s for s in user_servers if s["server_id"] == server_id), None)
        
        if not server:
            await callback.answer("❌ سرور یافت نشد!", show_alert=True)
            return
        
        user_servers = [s for s in user_servers if s["server_id"] != server_id]
        save_user_servers(user_id, user_servers)
        
        cursor.execute("UPDATE servers SET used_by=NULL, expiry=NULL WHERE id=?", (server_id,))
        db.commit()
        
        msg = get_message("delete_success") or DEFAULT_MESSAGES["delete_success"]
        msg = msg.format(server_name=server['name'])
        
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard("my_services"),
            parse_mode="HTML"
        )
        await callback.answer("✅ سرویس با موفقیت حذف شد!", show_alert=True)
        return
    
    if data.startswith("rename_"):
        server_id = int(data.split("_")[1])
        await state.update_data(rename_server_id=server_id)
        
        msg = get_message("rename_prompt") or DEFAULT_MESSAGES["rename_prompt"]
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard(f"view_server_{server_id}"),
            parse_mode="HTML"
        )
        await state.set_state(EditMessageState.waiting_for_rename)
        await callback.answer()
        return
    
    if data == "my_account":
        user_data = get_user_data(user_id)
        
        cursor.execute("SELECT first_name, username, joined_at FROM users WHERE user_id=?", (str(user_id),))
        user_info = cursor.fetchone()
        
        first_name = user_info[0] if user_info and user_info[0] else "نامشخص"
        username = user_info[1] if user_info and user_info[1] else "ندارد"
        joined_at = user_info[2] if user_info and user_info[2] else get_iran_time().isoformat()
        
        try:
            joined_date = datetime.fromisoformat(joined_at)
            joined_date = format_iran_time(joined_date)
        except:
            joined_date = joined_at
        
        user_servers = get_user_servers(user_id)
        active_servers = len(user_servers)
        wallet = get_wallet(user_id)
        warnings = get_warnings(user_id)
        
        msg = get_message("my_account") or DEFAULT_MESSAGES["my_account"]
        msg = msg.format(
            user_id=user_id,
            first_name=first_name,
            username=f"@{username}" if username != "ندارد" else "ندارد",
            active_servers=active_servers,
            total_servers=active_servers,
            joined_at=joined_date,
            today_count=user_data["daily_count"],
            wallet=wallet,
            warnings=warnings
        )
        
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard("back_to_main"),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    if data == "my_wallet":
        wallet = get_wallet(user_id)
        transactions = get_transactions(user_id)
        
        trans_text = ""
        if transactions:
            for amount, trans_type, desc, created_at in transactions:
                try:
                    created = datetime.fromisoformat(created_at)
                    created = format_iran_time(created)
                except:
                    created = created_at
                sign = "+" if amount > 0 else ""
                emoji = "💰" if amount > 0 else "💸"
                trans_text += f"{emoji} {sign}{amount} تومان - {desc} ({created})\n"
        else:
            trans_text = "هیچ تراکنشی وجود ندارد."
        
        msg = get_message("my_wallet") or DEFAULT_MESSAGES["my_wallet"]
        msg = msg.format(balance=wallet, transactions=trans_text)
        
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard("back_to_main"),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    if data == "help":
        msg = get_message("help") or DEFAULT_MESSAGES["help"]
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard("back_to_main"),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # ===== بخش مدیریت =====
    
    if data == "admin_panel" and int(user_id) == OWNER_ID:
        msg = get_message("admin_panel") or DEFAULT_MESSAGES["admin_panel"]
        await callback.message.edit_text(
            msg,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    if data == "admin_stats" and int(user_id) == OWNER_ID:
        total = get_total_servers()
        free = get_free_servers_count()
        used = get_used_servers_count()
        users = len(get_all_users())
        
        cursor.execute("SELECT id, used_by, ping FROM servers")
        servers = cursor.fetchall()
        details = ""
        for i, (sid, used_by, ping) in enumerate(servers, 1):
            status = "آزاد" if used_by is None else f"در اختیار کاربر {used_by}"
            ping_status = f" (پینگ: {ping}ms)" if ping and ping > 0 else ""
            details += f"\n{i}. سرور {sid} - {status}{ping_status}"
        
        msg = get_message("admin_stats") or DEFAULT_MESSAGES["admin_stats"]
        msg = msg.format(total=total, free=free, used=used, users=users, details=details)
        
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard("admin_panel"),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    if data == "admin_add_servers" and int(user_id) == OWNER_ID:
        msg = get_message("admin_add_prompt") or DEFAULT_MESSAGES["admin_add_prompt"]
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard("admin_panel"),
            parse_mode="HTML"
        )
        await state.set_state(EditMessageState.waiting_for_config)
        await callback.answer()
        return
    
    if data == "admin_remove_server" and int(user_id) == OWNER_ID:
        cursor.execute("SELECT id, used_by FROM servers")
        servers = cursor.fetchall()
        
        if not servers:
            await callback.message.edit_text(
                "📭 هیچ سروری برای حذف وجود نداره!",
                reply_markup=get_back_keyboard("admin_panel")
            )
            await callback.answer()
            return
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for sid, used_by in servers:
            status = "آزاد" if used_by is None else f"مشغول ({used_by})"
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(f"🗑 سرور {sid} - {status}", callback_data=f"remove_server_{sid}")
            ])
        keyboard.inline_keyboard.append([
            InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")
        ])
        
        msg = get_message("admin_remove_prompt") or DEFAULT_MESSAGES["admin_remove_prompt"]
        await callback.message.edit_text(msg, reply_markup=keyboard)
        await callback.answer()
        return
    
    if data.startswith("remove_server_") and int(user_id) == OWNER_ID:
        server_id = int(data.split("_")[2])
        remove_server(server_id)
        
        msg = get_message("admin_remove_success") or DEFAULT_MESSAGES["admin_remove_success"]
        msg = msg.format(id=server_id)
        
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard("admin_panel"),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    if data == "admin_users" and int(user_id) == OWNER_ID:
        users = get_all_users()
        
        if not users:
            await callback.message.edit_text(
                "📭 هیچ کاربری ثبت نشده!",
                reply_markup=get_back_keyboard("admin_panel")
            )
            await callback.answer()
            return
        
        users_text = ""
        for uid, daily_count, servers, first_name, username, joined_at, wallet, warnings, is_banned in users:
            try:
                servers_list = json.loads(servers) if servers else []
            except:
                servers_list = eval(servers) if servers else []
            status = "🚫" if is_banned == 1 else "✅"
            users_text += f"🆔 `{uid}` - {first_name or 'بدون نام'} (@{username or 'بدون یوزر'}) - {len(servers_list)} سرور - 💰{wallet} تومان - ⚠️{warnings} {status}\n"
        
        msg = get_message("admin_users_list") or DEFAULT_MESSAGES["admin_users_list"]
        msg = msg.format(users=users_text)
        
        if len(msg) > 4000:
            with open("users_list.txt", "w", encoding="utf-8") as f:
                f.write(msg)
            await callback.message.answer_document(
                types.FSInputFile("users_list.txt"),
                caption="📋 لیست کامل کاربران",
                reply_markup=get_back_keyboard("admin_panel")
            )
            os.remove("users_list.txt")
            await callback.message.delete()
        else:
            await callback.message.edit_text(
                msg,
                reply_markup=get_back_keyboard("admin_panel"),
                parse_mode="HTML"
            )
        await callback.answer()
        return
    
    if data == "admin_edit_messages" and int(user_id) == OWNER_ID:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        
        message_names = [
            "welcome", "help", "server_building", "server_created", 
            "no_free_servers", "daily_limit", "no_services", "server_info",
            "rename_prompt", "rename_confirmed", "my_account", "my_wallet",
            "ping_result", "report_prompt", "report_sent", "delete_confirmation",
            "delete_success", "qr_code_sent", "config_sent", "server_updated_notification",
            "required_channels_check", "required_channels_ok", "required_channels_fail"
        ]
        
        for name in message_names:
            display_name = name.replace("_", " ").title()
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(f"✏️ {display_name}", callback_data=f"edit_msg_{name}")
            ])
        keyboard.inline_keyboard.append([
            InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")
        ])
        
        msg = get_message("admin_edit_messages") or DEFAULT_MESSAGES["admin_edit_messages"]
        await callback.message.edit_text(msg, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return
    
    if data.startswith("edit_msg_") and int(user_id) == OWNER_ID:
        msg_name = data.replace("edit_msg_", "")
        await state.update_data(editing_msg_name=msg_name)
        
        msg = get_message("admin_edit_prompt") or DEFAULT_MESSAGES["admin_edit_prompt"]
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard("admin_edit_messages"),
            parse_mode="HTML"
        )
        await state.set_state(EditMessageState.waiting_for_text)
        await callback.answer()
        return
    
    if data == "admin_ping_reports" and int(user_id) == OWNER_ID:
        reports = get_pending_ping_reports()
        
        if not reports:
            await callback.message.edit_text(
                "📊 هیچ گزارش پینگ بالایی وجود ندارد!",
                reply_markup=get_back_keyboard("admin_panel")
            )
            await callback.answer()
            return
        
        reports_text = ""
        for report_id, server_id, user_id, ping, reported_at, status in reports:
            reports_text += f"\n🆔 سرور: {server_id}\n👤 کاربر: {user_id}\n📊 پینگ: {ping}ms\n⏰ زمان: {reported_at}\n{'-'*30}"
        
        msg = get_message("ping_reports_list") or DEFAULT_MESSAGES["ping_reports_list"]
        msg = msg.format(reports=reports_text)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("✅ تایید همه", callback_data="confirm_all_pings")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ])
        
        await callback.message.edit_text(msg, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return
    
    if data == "confirm_all_pings" and int(user_id) == OWNER_ID:
        cursor.execute("UPDATE ping_reports SET status='confirmed'")
        db.commit()
        await callback.message.edit_text(
            "✅ همه گزارش‌های پینگ تایید شدند!",
            reply_markup=get_back_keyboard("admin_panel")
        )
        await callback.answer()
        return
    
    if data == "admin_update_service" and int(user_id) == OWNER_ID:
        msg = get_message("update_service_prompt") or DEFAULT_MESSAGES["update_service_prompt"]
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard("admin_panel"),
            parse_mode="HTML"
        )
        await state.set_state(EditMessageState.waiting_for_update)
        await callback.answer()
        return
    
    if data == "admin_server_reports" and int(user_id) == OWNER_ID:
        reports = get_pending_server_reports()
        
        if not reports:
            await callback.message.edit_text(
                "📊 هیچ گزارش خرابی وجود ندارد!",
                reply_markup=get_back_keyboard("admin_panel")
            )
            await callback.answer()
            return
        
        reports_text = ""
        for report_id, server_id, user_id, report_text, reported_at, status in reports:
            reports_text += f"\n🆔 سرور: {server_id}\n👤 کاربر: {user_id}\n📝 گزارش: {report_text}\n⏰ زمان: {reported_at}\n{'-'*30}"
        
        msg = get_message("server_reports_list") or DEFAULT_MESSAGES["server_reports_list"]
        msg = msg.format(reports=reports_text)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("✅ بررسی شد", callback_data="confirm_all_reports")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ])
        
        await callback.message.edit_text(msg, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return
    
    if data == "confirm_all_reports" and int(user_id) == OWNER_ID:
        cursor.execute("UPDATE server_reports SET status='resolved'")
        db.commit()
        await callback.message.edit_text(
            "✅ همه گزارش‌ها بررسی شدند!",
            reply_markup=get_back_keyboard("admin_panel")
        )
        await callback.answer()
        return
    
    if data == "admin_required_channels" and int(user_id) == OWNER_ID:
        await callback.message.edit_text(
            "📢 **مدیریت چنل‌های اجباری**\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=get_channel_management_keyboard()
        )
        await callback.answer()
        return
    
    if data == "add_required_channel" and int(user_id) == OWNER_ID:
        channels = get_required_channels()
        if len(channels) >= 10:
            await callback.message.edit_text(
                "❌ **حداکثر ۱۰ چنل قابل اضافه شدن است!**\n\nلطفاً ابتدا یک چنل را حذف کنید.",
                reply_markup=get_back_keyboard("admin_required_channels")
            )
            await callback.answer("❌ حداکثر ۱۰ چنل!", show_alert=True)
            return
        
        msg = get_message("required_channels_prompt") or DEFAULT_MESSAGES["required_channels_prompt"]
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard("admin_required_channels"),
            parse_mode="HTML"
        )
        await state.set_state(EditMessageState.waiting_for_channel)
        await callback.answer()
        return
    
    if data == "list_required_channels" and int(user_id) == OWNER_ID:
        channels = get_required_channels()
        
        if not channels:
            await callback.message.edit_text(
                "📢 **هیچ چنل اجباری تنظیم نشده است!**\n\nبرای افزودن چنل از دکمه زیر استفاده کنید.",
                reply_markup=get_channel_management_keyboard()
            )
            await callback.answer()
            return
        
        channels_text = ""
        for i, ch in enumerate(channels, 1):
            channels_text += f"{i}. @{ch}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for i, ch in enumerate(channels):
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(f"🗑 حذف @{ch}", callback_data=f"remove_required_{ch}")
            ])
        keyboard.inline_keyboard.append([
            InlineKeyboardButton("🔙 بازگشت", callback_data="admin_required_channels")
        ])
        
        msg = get_message("required_channels_list") or DEFAULT_MESSAGES["required_channels_list"]
        msg = msg.format(channels=channels_text, count=len(channels))
        
        await callback.message.edit_text(msg, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return
    
    if data.startswith("remove_required_") and int(user_id) == OWNER_ID:
        channel = data.replace("remove_required_", "")
        channels = get_required_channels()
        
        if channel in channels:
            channels.remove(channel)
            set_required_channels(channels)
            
            msg = get_message("required_channel_removed") or DEFAULT_MESSAGES["required_channel_removed"]
            msg = msg.format(channel=channel)
            
            await callback.message.edit_text(
                msg,
                reply_markup=get_channel_management_keyboard(),
                parse_mode="HTML"
            )
            await callback.answer(f"✅ چنل @{channel} حذف شد!", show_alert=True)
        else:
            await callback.message.edit_text(
                "❌ چنل مورد نظر یافت نشد!",
                reply_markup=get_channel_management_keyboard()
            )
            await callback.answer()
        return
    
    if data == "admin_wallet" and int(user_id) == OWNER_ID:
        msg = get_message("admin_wallet_prompt") or DEFAULT_MESSAGES["admin_wallet_prompt"]
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard("admin_panel"),
            parse_mode="HTML"
        )
        await state.set_state(EditMessageState.waiting_for_wallet)
        await callback.answer()
        return
    
    if data == "admin_warnings" and int(user_id) == OWNER_ID:
        msg = get_message("admin_warnings_prompt") or DEFAULT_MESSAGES["admin_warnings_prompt"]
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard("admin_panel"),
            parse_mode="HTML"
        )
        await state.set_state(EditMessageState.waiting_for_warnings)
        await callback.answer()
        return
    
    if data == "admin_set_emoji" and int(user_id) == OWNER_ID:
        msg = get_message("admin_set_emoji_prompt") or DEFAULT_MESSAGES["admin_set_emoji_prompt"]
        await callback.message.edit_text(
            msg,
            reply_markup=get_back_keyboard("admin_panel"),
            parse_mode="HTML"
        )
        await state.set_state(EditMessageState.waiting_for_emoji)
        await callback.answer()
        return
    
    await callback.answer()

# ==================== هندلرهای پیام متنی ====================

@dp.message(EditMessageState.waiting_for_text)
async def handle_edit_message(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        return
    
    data = await state.get_data()
    msg_name = data.get("editing_msg_name")
    
    if message.text.lower() == "/cancel":
        await state.clear()
        await message.answer("❌ عملیات ویرایش لغو شد.", reply_markup=get_main_keyboard(user_id))
        return
    
    save_message(msg_name, message.text)
    
    msg = get_message("admin_edit_success") or DEFAULT_MESSAGES["admin_edit_success"]
    await message.answer(msg, reply_markup=get_back_keyboard("admin_edit_messages"))
    await state.clear()

@dp.message(EditMessageState.waiting_for_config)
async def handle_add_servers(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        return
    
    if message.text.lower() == "/cancel":
        await state.clear()
        await message.answer("❌ عملیات افزودن سرور لغو شد.", reply_markup=get_main_keyboard(user_id))
        return
    
    configs = [line.strip() for line in message.text.split('\n') if line.strip()]
    
    if not configs:
        await message.answer("❌ هیچ کانفیگ معتبری یافت نشد!\nلطفاً دوباره تلاش کنید.", reply_markup=get_main_keyboard(user_id))
        return
    
    added = 0
    for config in configs:
        ip = "Unknown"
        port = "Unknown"
        try:
            if "@" in config:
                parts = config.split("@")
                if len(parts) > 1:
                    ip_port = parts[1].split("?")[0].split(":")
                    if len(ip_port) >= 2:
                        ip = ip_port[0]
                        port = ip_port[1]
        except:
            pass
        
        add_server(config, ip, port)
        added += 1
    
    msg = get_message("admin_add_success") or DEFAULT_MESSAGES["admin_add_success"]
    msg = msg.format(
        count=added,
        total=get_total_servers(),
        id_range=f"{get_total_servers() - added + 1} تا {get_total_servers()}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("📊 مشاهده آمار", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin_panel")]
    ])
    
    await message.answer(msg, reply_markup=keyboard, parse_mode="HTML")
    await state.clear()

@dp.message(EditMessageState.waiting_for_channel)
async def handle_add_channel(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        return
    
    if message.text.lower() == "/cancel":
        await state.clear()
        await message.answer("❌ عملیات لغو شد.", reply_markup=get_main_keyboard(user_id))
        return
    
    channel = message.text.strip().replace("@", "").strip()
    
    if not channel:
        await message.answer("❌ یوزرنیم چنل معتبر نیست!\nلطفاً دوباره تلاش کنید.", reply_markup=get_main_keyboard(user_id))
        return
    
    channels = get_required_channels()
    
    if len(channels) >= 10:
        await message.answer("❌ **حداکثر ۱۰ چنل قابل اضافه شدن است!**\n\nلطفاً ابتدا یک چنل را حذف کنید.", reply_markup=get_back_keyboard("admin_required_channels"))
        return
    
    if channel in channels:
        await message.answer(f"❌ چنل @{channel} قبلاً اضافه شده است!", reply_markup=get_back_keyboard("admin_required_channels"))
        return
    
    try:
        await bot.get_chat_member(f"@{channel}", bot.id)
    except:
        await message.answer(f"❌ **ربات ادمین چنل @{channel} نیست!**\n\nلطفاً ابتدا ربات را ادمین چنل کنید.", reply_markup=get_back_keyboard("admin_required_channels"))
        return
    
    channels.append(channel)
    set_required_channels(channels)
    
    channels_text = "\n".join([f"• @{ch}" for ch in channels])
    msg = get_message("required_channels_set") or DEFAULT_MESSAGES["required_channels_set"]
    msg = msg.format(channels=channels_text)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("📋 لیست چنل‌ها", callback_data="list_required_channels")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_required_channels")]
    ])
    
    await message.answer(msg, reply_markup=keyboard, parse_mode="HTML")
    await state.clear()

@dp.message(EditMessageState.waiting_for_wallet)
async def handle_wallet(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        return
    
    if message.text.lower() == "/cancel":
        await state.clear()
        await message.answer("❌ عملیات لغو شد.", reply_markup=get_main_keyboard(user_id))
        return
    
    try:
        parts = message.text.split("|")
        if len(parts) < 3:
            await message.answer("❌ فرمت ورودی صحیح نیست!\nلطفاً به فرمت `افزایش|آیدی|مبلغ` یا `کاهش|آیدی|مبلغ` ارسال کنید.", reply_markup=get_main_keyboard(user_id))
            return
        
        action = parts[0].strip()
        target_id = parts[1].strip()
        amount = int(parts[2].strip())
        
        if action not in ["افزایش", "کاهش"]:
            await message.answer("❌ نوع عملیات باید 'افزایش' یا 'کاهش' باشد!", reply_markup=get_main_keyboard(user_id))
            return
        
        if amount <= 0:
            await message.answer("❌ مبلغ باید بیشتر از صفر باشد!", reply_markup=get_main_keyboard(user_id))
            return
        
        user_data = get_user_data(target_id)
        if not user_data:
            await message.answer(f"❌ کاربر با آیدی {target_id} یافت نشد!", reply_markup=get_main_keyboard(user_id))
            return
        
        if action == "افزایش":
            new_balance = add_wallet(target_id, amount)
            add_transaction(target_id, amount, "افزایش", "افزایش موجودی توسط ادمین")
            trans_type = "افزایش"
        else:
            success = deduct_wallet(target_id, amount)
            if not success:
                await message.answer(f"❌ موجودی کاربر {target_id} کافی نیست!", reply_markup=get_main_keyboard(user_id))
                return
            new_balance = get_wallet(target_id)
            add_transaction(target_id, -amount, "کاهش", "کاهش موجودی توسط ادمین")
            trans_type = "کاهش"
        
        msg = get_message("admin_wallet_success") or DEFAULT_MESSAGES["admin_wallet_success"]
        msg = msg.format(
            user_id=target_id,
            balance=new_balance,
            type=trans_type,
            amount=amount
        )
        
        try:
            await bot.send_message(
                int(target_id),
                f"💰 **تغییر موجودی کیف پول!**\n\n📝 {trans_type} موجودی به مبلغ {amount} تومان\n💰 موجودی جدید: {new_balance} تومان",
                parse_mode="HTML"
            )
        except:
            pass
        
        await message.answer(msg, reply_markup=get_main_keyboard(user_id), parse_mode="HTML")
        await state.clear()
        
    except ValueError:
        await message.answer("❌ مبلغ باید عدد باشد!\nلطفاً دوباره تلاش کنید.", reply_markup=get_main_keyboard(user_id))
    except Exception as e:
        await message.answer(f"❌ خطا: {str(e)}", reply_markup=get_main_keyboard(user_id))

@dp.message(EditMessageState.waiting_for_warnings)
async def handle_warnings(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        return
    
    if message.text.lower() == "/cancel":
        await state.clear()
        await message.answer("❌ عملیات لغو شد.", reply_markup=get_main_keyboard(user_id))
        return
    
    try:
        parts = message.text.split("|")
        action = parts[0].strip()
        
        if action == "لیست":
            conn = sqlite3.connect("bot.db", check_same_thread=False)
            c = conn.cursor()
            try:
                c.execute("SELECT user_id, first_name, username, warnings, is_banned FROM users WHERE warnings > 0 ORDER BY warnings DESC")
                users = c.fetchall()
            finally:
                conn.close()
            
            if not users:
                await message.answer("📋 هیچ کاربری با اخطار وجود ندارد!", reply_markup=get_main_keyboard(user_id))
                return
            
            users_text = ""
            for uid, first_name, username, warnings, is_banned in users:
                status = "🚫 مسدود" if is_banned == 1 else "✅ فعال"
                users_text += f"🆔 `{uid}` - {first_name or 'بدون نام'} (@{username or 'بدون یوزر'}) - ⚠️{warnings} - {status}\n"
            
            msg = get_message("admin_warnings_list") or DEFAULT_MESSAGES["admin_warnings_list"]
            msg = msg.format(users=users_text)
            
            await message.answer(msg, reply_markup=get_main_keyboard(user_id), parse_mode="HTML")
            return
        
        if len(parts) < 2:
            await message.answer("❌ فرمت ورودی صحیح نیست!\nلطفاً به فرمت `افزایش|آیدی` یا `حذف|آیدی` ارسال کنید.", reply_markup=get_main_keyboard(user_id))
            return
        
        target_id = parts[1].strip()
        user_data = get_user_data(target_id)
        
        if not user_data:
            await message.answer(f"❌ کاربر با آیدی {target_id} یافت نشد!", reply_markup=get_main_keyboard(user_id))
            return
        
        if action == "افزایش":
            blocked, warnings, is_banned = add_warning(target_id)
            status_text = "🚫 مسدود" if is_banned else "✅ فعال"
            
            msg = get_message("admin_warnings_success") or DEFAULT_MESSAGES["admin_warnings_success"]
            msg = msg.format(
                user_id=target_id,
                warnings=warnings,
                status=status_text
            )
            
            if is_banned:
                try:
                    await bot.send_message(
                        int(target_id),
                        f"🚫 **شما به دلیل ۳ اخطار مسدود شدید!**\nبرای رفع مسدودیت با پشتیبانی تماس بگیرید.",
                        parse_mode="HTML"
                    )
                except:
                    pass
            
            await message.answer(msg, reply_markup=get_main_keyboard(user_id), parse_mode="HTML")
            
        elif action == "حذف":
            conn = sqlite3.connect("bot.db", check_same_thread=False)
            c = conn.cursor()
            try:
                c.execute("UPDATE users SET warnings=0, is_banned=0 WHERE user_id=?", (str(target_id),))
                conn.commit()
            finally:
                conn.close()
            
            msg = get_message("admin_warnings_cleared") or DEFAULT_MESSAGES["admin_warnings_cleared"]
            msg = msg.format(user_id=target_id)
            
            try:
                await bot.send_message(
                    int(target_id),
                    f"✅ **اخطارهای شما پاک شد!**\nشما می‌توانید مجدداً از ربات استفاده کنید.",
                    parse_mode="HTML"
                )
            except:
                pass
            
            await message.answer(msg, reply_markup=get_main_keyboard(user_id), parse_mode="HTML")
            
        else:
            await message.answer("❌ عمل نامعتبر! لطفاً از 'افزایش'، 'حذف' یا 'لیست' استفاده کنید.", reply_markup=get_main_keyboard(user_id))
            
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ خطا: {str(e)}", reply_markup=get_main_keyboard(user_id))

@dp.message(EditMessageState.waiting_for_emoji)
async def handle_set_emoji(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        return
    
    if message.text.lower() == "/cancel":
        await state.clear()
        await message.answer("❌ عملیات لغو شد.", reply_markup=get_main_keyboard(user_id))
        return
    
    emoji_id = message.text.strip()
    
    if not emoji_id or not emoji_id.isdigit():
        await message.answer("❌ کد ایموجی معتبر نیست!\nلطفاً یک کد عددی معتبر وارد کنید.", reply_markup=get_main_keyboard(user_id))
        return
    
    set_welcome_emoji(emoji_id)
    
    msg = get_message("admin_set_emoji_success") or DEFAULT_MESSAGES["admin_set_emoji_success"]
    msg = msg.format(emoji_id=emoji_id)
    
    await message.answer(msg, reply_markup=get_back_keyboard("admin_panel"), parse_mode="HTML")
    await state.clear()

@dp.message(EditMessageState.waiting_for_update)
async def handle_update_service(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        return
    
    if message.text.lower() == "/cancel":
        await state.clear()
        await message.answer("❌ عملیات آپدیت لغو شد.", reply_markup=get_main_keyboard(user_id))
        return
    
    if "|" not in message.text:
        await message.answer("❌ فرمت ورودی صحیح نیست!\nلطفاً به فرمت `سرور_آی‌دی|کانفیگ_جدید` ارسال کنید.", reply_markup=get_main_keyboard(user_id))
        return
    
    try:
        server_id_str, new_config = message.text.split("|", 1)
        server_id = int(server_id_str.strip())
        new_config = new_config.strip()
        
        server = get_server_by_id(server_id)
        if not server:
            await message.answer(f"❌ سرور با آی‌دی {server_id} یافت نشد!", reply_markup=get_main_keyboard(user_id))
            return
        
        user_id_of_server = server[5]
        if not user_id_of_server:
            await message.answer(f"❌ سرور {server_id} به هیچ کاربری اختصاص داده نشده!", reply_markup=get_main_keyboard(user_id))
            return
        
        update_server_config(server_id, new_config)
        
        user_servers = get_user_servers(user_id_of_server)
        for s in user_servers:
            if s["server_id"] == server_id:
                hashtag = ""
                if " " in s["config"]:
                    hashtag = s["config"].split(" ")[-1] if s["config"].split(" ")[-1].startswith("#") else ""
                elif "#" in s["config"]:
                    hashtag_match = re.search(r'#\S+', s["config"])
                    if hashtag_match:
                        hashtag = hashtag_match.group()
                
                if hashtag:
                    new_config_with_hashtag = f"{new_config} {hashtag}"
                else:
                    username = f"user{user_id_of_server}"
                    new_config_with_hashtag = add_hashtag_to_config(new_config, user_id_of_server, username)
                
                s["config"] = new_config_with_hashtag
                break
        
        save_user_servers(user_id_of_server, user_servers)
        
        update_msg = get_message("server_updated_notification") or DEFAULT_MESSAGES["server_updated_notification"]
        update_msg = update_msg.format(server_name=f"سرور {server_id}")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("📋 سرویس‌های من", callback_data="my_services")]
        ])
        
        await bot.send_message(int(user_id_of_server), update_msg, reply_markup=keyboard, parse_mode="HTML")
        
        await message.answer(f"✅ سرویس سرور {server_id} با موفقیت آپدیت شد!\nکاربر {user_id_of_server} مطلع شد.", reply_markup=get_main_keyboard(user_id))
        await state.clear()
        
    except ValueError:
        await message.answer("❌ آی‌دی سرور باید عدد باشد!\nلطفاً به فرمت `سرور_آی‌دی|کانفیگ_جدید` ارسال کنید.", reply_markup=get_main_keyboard(user_id))
    except Exception as e:
        await message.answer(f"❌ خطا در آپدیت سرویس: {str(e)}", reply_markup=get_main_keyboard(user_id))

@dp.message(EditMessageState.waiting_for_rename)
async def handle_rename(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if message.text.lower() == "/cancel":
        await state.clear()
        await message.answer("❌ عملیات تغییر نام لغو شد.", reply_markup=get_main_keyboard(user_id))
        return
    
    data = await state.get_data()
    server_id = data.get("rename_server_id")
    
    if not server_id:
        await message.answer("❌ خطا! سرور مورد نظر یافت نشد.", reply_markup=get_main_keyboard(user_id))
        await state.clear()
        return
    
    new_name = message.text.strip()
    
    if not new_name:
        await message.answer("❌ نام نمی‌تواند خالی باشد!\nلطفاً دوباره تلاش کنید.", reply_markup=get_main_keyboard(user_id))
        return
    
    user_servers = get_user_servers(user_id)
    
    found = False
    for server in user_servers:
        if server["server_id"] == server_id:
            server["name"] = new_name
            found = True
            break
    
    if not found:
        await message.answer("❌ سرور مورد نظر یافت نشد!", reply_markup=get_main_keyboard(user_id))
        await state.clear()
        return
    
    save_user_servers(user_id, user_servers)
    
    msg = get_message("rename_confirmed") or DEFAULT_MESSAGES["rename_confirmed"]
    msg = msg.format(new_name=new_name)
    
    await message.answer(msg, reply_markup=get_back_keyboard("my_services"), parse_mode="HTML")
    await state.clear()

@dp.message(EditMessageState.waiting_for_report)
async def handle_report(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if message.text.lower() == "/cancel":
        await state.clear()
        await message.answer("❌ عملیات گزارش لغو شد.", reply_markup=get_main_keyboard(user_id))
        return
    
    data = await state.get_data()
    server_id = data.get("report_server_id")
    
    if not server_id:
        await message.answer("❌ خطا! سرور مورد نظر یافت نشد.", reply_markup=get_main_keyboard(user_id))
        await state.clear()
        return
    
    report_text = message.text
    
    save_server_report(server_id, user_id, report_text)
    
    msg = get_message("report_sent") or DEFAULT_MESSAGES["report_sent"]
    msg = msg.format(
        server_name=f"سرور {server_id}",
        report_text=report_text
    )
    
    await message.answer(msg, reply_markup=get_back_keyboard("my_services"), parse_mode="HTML")
    
    owner_msg = get_message("admin_report_notification") or DEFAULT_MESSAGES["admin_report_notification"]
    owner_msg = owner_msg.format(
        server_id=server_id,
        user_id=user_id,
        report_text=report_text,
        time=format_iran_time(get_iran_time())
    )
    
    await bot.send_message(OWNER_ID, owner_msg, parse_mode="HTML")
    await state.clear()

# ==================== اجرای اصلی ====================
async def main():
    print("🤖 ربات با Aiogram روشن شد!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
