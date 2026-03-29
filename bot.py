import requests
import telebot
import whois
import re
from datetime import datetime
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import io
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
import os
import sqlite3
import random

TOKEN = "8727461047:AAHaWiD9PoExQdid_fDc4Gc2sJRSC3VGLcI"
VT_KEY = "1992e6ca7eb6474426aedee99d9743ce9d93938e75118f899f4ef25a7b6dedbb"
ADMIN_ID = 8471318803

bot = telebot.TeleBot(TOKEN)

# ========== БАЗА ДАННЫХ ==========
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_seen TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS checks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, url TEXT, result TEXT, date TEXT)''')
conn.commit()

# ========== ХРАНИЛИЩЕ ПОЛЬЗОВАТЕЛЕЙ ==========
users = set()

# ========== КНОПКИ ==========
def main_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_check = KeyboardButton("🔍 Проверить ссылку")
    btn_history = KeyboardButton("📜 История")
    btn_help = KeyboardButton("📖 Помощь")
    btn_info = KeyboardButton("ℹ️ О боте")
    markup.add(btn_check, btn_history, btn_help, btn_info)
    return markup

def cancel_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("❌ Отмена"))
    return markup

# ========== РАСКРЫТИЕ ССЫЛОК ==========
def expand_url(url):
    try:
        response = requests.get(url, allow_redirects=True, timeout=5)
        return response.url
    except:
        return url

# ========== СКРИНШОТ ==========
def take_screenshot(url):
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        service = Service('/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)
        time.sleep(2)
        screenshot = driver.get_screenshot_as_png()
        driver.quit()
        return Image.open(io.BytesIO(screenshot))
    except:
        return None

# ========== ПРОВЕРКИ ==========
def vt_check(url):
    try:
        r = requests.get('https://www.virustotal.com/vtapi/v2/url/report', params={'apikey': VT_KEY, 'resource': url})
        d = r.json()
        if d.get('response_code') == 1:
            p = d.get('positives', 0)
            t = d.get('total', 0)
            return ('danger', f'⚠️ {p}/{t} антивирусов обнаружили угрозы') if p > 0 else ('safe', f'✅ {p}/{t} антивирусов — чисто')
        return ('unknown', '❓ Ссылка не найдена в базах VirusTotal')
    except:
        return ('error', '❌ Ошибка подключения к VirusTotal')

def whois_check(domain):
    try:
        w = whois.whois(domain)
        if w.creation_date:
            c = w.creation_date[0] if isinstance(w.creation_date, list) else w.creation_date
            days = (datetime.now() - c).days
            if days < 7: return ('danger', f'⚠️ Домен зарегистрирован {days} дней назад! КРАЙНЕ ПОДОЗРИТЕЛЬНО')
            if days < 30: return ('danger', f'⚠️ Домен зарегистрирован {days} дней назад. Очень подозрительно')
            if days < 90: return ('warning', f'⚠️ Домен зарегистрирован {days} дней назад')
            return ('safe', f'✅ Домен зарегистрирован {days} дней назад')
        return ('warning', '⚠️ Не удалось определить возраст домена')
    except:
        return ('warning', '⚠️ WHOIS недоступен')

def bad_words(url):
    words = ['login', 'secure', 'verify', 'account', 'bank', 'paypal', 'apple', 'microsoft', 'confirm', 'update', 'signin', 'auth', 'password', 'webscr', 'identity', 'verification']
    return [w for w in words if w in url.lower()]

def check_ssl(domain):
    try:
        import ssl
        import socket
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                return '✅ SSL сертификат есть'
    except:
        return '⚠️ SSL сертификат отсутствует или недействителен'

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start(m):
    users.add(m.chat.id)
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_seen) VALUES (?, ?, ?)", 
                   (m.chat.id, m.from_user.username, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    
    bot.send_message(m.chat.id, 
        "🛡️ **REVERS | Проверка ссылок**\n\n"
        "🔍 Отправь ссылку для проверки безопасности.\n"
        "📜 История проверок — в меню.\n\n"
        "Нажми **🔍 Проверить ссылку**, чтобы начать.",
        reply_markup=main_keyboard(),
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['help'])
def help_cmd(m):
    bot.send_message(m.chat.id,
        "📖 **Инструкция**\n\n"
        "🔍 **Проверить ссылку** — введи любую ссылку\n"
        "📜 **История** — последние 10 проверок\n\n"
        "Бот проверяет:\n"
        "• VirusTotal (репутация)\n"
        "• Возраст домена (whois)\n"
        "• Подозрительные слова\n"
        "• SSL сертификат\n"
        "• Раскрывает короткие ссылки\n"
        "• Делает скриншот\n\n"
        "Команды:\n"
        "/start — приветствие\n"
        "/check ссылка — быстрая проверка\n"
        "/broadcast текст — рассылка (только админ)",
        reply_markup=main_keyboard(),
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['broadcast'])
def broadcast(m):
    if m.chat.id != ADMIN_ID:
        bot.reply_to(m, "⛔ Доступ запрещён.")
        return
    msg = m.text.split(maxsplit=1)
    if len(msg) < 2:
        bot.reply_to(m, "❌ Укажи текст рассылки.\nПример: /broadcast Привет!")
        return
    text = msg[1]
    bot.reply_to(m, f"📢 Рассылка запущена для {len(users)} пользователей...")
    for uid in users:
        try:
            bot.send_message(uid, text)
        except:
            pass
    bot.reply_to(m, "✅ Рассылка завершена.")

@bot.message_handler(func=lambda m: m.text == "🔍 Проверить ссылку")
def ask_url(m):
    msg = bot.send_message(m.chat.id, "🔗 Отправь ссылку для проверки:", reply_markup=cancel_keyboard())
    bot.register_next_step_handler(msg, check_url)

@bot.message_handler(func=lambda m: m.text == "📜 История")
def show_history(m):
    cursor.execute("SELECT url, result, date FROM checks WHERE user_id = ? ORDER BY id DESC LIMIT 10", (m.chat.id,))
    rows = cursor.fetchall()
    if not rows:
        bot.send_message(m.chat.id, "📜 История пуста. Проверь первую ссылку!", reply_markup=main_keyboard())
        return
    msg = "📜 **Последние проверки:**\n\n"
    for i, row in enumerate(rows, 1):
        msg += f"{i}. {row[0]}\n   {row[1]}\n   _{row[2]}_\n\n"
    bot.send_message(m.chat.id, msg, reply_markup=main_keyboard(), parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "📖 Помощь")
def help_button(m):
    help_cmd(m)

@bot.message_handler(func=lambda m: m.text == "ℹ️ О боте")
def about(m):
    bot.send_message(m.chat.id,
        "ℹ️ **О боте**\n\n"
        "**REVERS** — инструмент для проверки ссылок.\n\n"
        "⚙️ **Функции:**\n"
        "• Проверка через VirusTotal\n"
        "• Анализ возраста домена\n"
        "• Поиск подозрительных слов\n"
        "• Проверка SSL сертификата\n"
        "• Раскрытие коротких ссылок\n"
        "• Скриншот страницы\n"
        "• История проверок\n\n"
        "📌 **Версия:** 3.0\n"
        "📌 **Канал:** <https://t.me/+QTjW7b6ZU1VhODVl>",
        reply_markup=main_keyboard(),
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda m: m.text == "❌ Отмена")
def cancel(m):
    bot.send_message(m.chat.id, "❌ Действие отменено.", reply_markup=main_keyboard())

def check_url(m):
    url = m.text.strip()
    if url == "❌ Отмена":
        cancel(m)
        return
    
    bot.send_chat_action(m.chat.id, 'typing')
    
    # Раскрываем короткую ссылку
    original = url
    expanded = expand_url(url)
    if expanded != url:
        bot.send_message(m.chat.id, f"🔗 Короткая ссылка раскрыта:\n{expanded}")
        url = expanded
    
    # Определяем домен
    domain = re.findall(r'https?://([^/]+)', url)
    domain = domain[0] if domain else url
    domain = domain.split('/')[0]
    
    # Проверки
    vt_status, vt_msg = vt_check(url)
    who_status, who_msg = whois_check(domain)
    bad = bad_words(url)
    ssl_msg = check_ssl(domain)
    
    # Формируем результат
    msg = f"🔍 **REVERS | Результат проверки**\n\n"
    msg += f"📎 **Ссылка:** `{url}`\n"
    msg += f"🌐 **Домен:** `{domain}`\n\n"
    msg += f"🛡️ **VirusTotal:** {vt_msg}\n"
    msg += f"📅 **WHOIS:** {who_msg}\n"
    msg += f"🔒 **SSL:** {ssl_msg}\n"
    
    if bad:
        msg += f"⚠️ **Подозрительные слова:** {', '.join(bad)}\n"
    else:
        msg += f"✅ **Подозрительных слов:** не найдено\n"
    
    # Вердикт
    msg += f"\n"
    if vt_status == 'danger' or who_status == 'danger' or bad:
        msg += "🚨 **ВЕРДИКТ: ССЫЛКА ОПАСНА!**\n"
        msg += "❌ Не переходи по ссылке.\n"
        msg += "❌ Не вводи личные данные.\n"
        msg += "❌ Не скачивай файлы."
        result = "ОПАСНО"
    elif vt_status == 'warning' or who_status == 'warning':
        msg += "⚠️ **ВЕРДИКТ: ПОДОЗРИТЕЛЬНАЯ ССЫЛКА**\n"
        msg += "Будь осторожен, проверяй адрес вручную."
        result = "ПОДОЗРИТЕЛЬНО"
    else:
        msg += "✅ **ВЕРДИКТ: БЕЗОПАСНО**\n"
        msg += "Но всегда проверяй адрес сайта вручную."
        result = "БЕЗОПАСНО"
    
    msg += f"\n\n🛡️ REVERS | Ваш защитник в сети"
    
    bot.send_message(m.chat.id, msg, reply_markup=main_keyboard(), parse_mode='Markdown')
    
    # Сохраняем в историю
    cursor.execute("INSERT INTO checks (user_id, url, result, date) VALUES (?, ?, ?, ?)",
                   (m.chat.id, url[:100], result, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    
    # Делаем скриншот (только для безопасных ссылок, чтобы не рисковать)
    if vt_status != 'danger' and who_status != 'danger':
        bot.send_message(m.chat.id, "📸 Делаю скриншот страницы...")
        screenshot = take_screenshot(url)
        if screenshot:
            bio = io.BytesIO()
            screenshot.save(bio, 'PNG')
            bio.seek(0)
            bot.send_photo(m.chat.id, bio, caption="📸 Скриншот страницы:")
        else:
            bot.send_message(m.chat.id, "❌ Не удалось сделать скриншот.")
    else:
        bot.send_message(m.chat.id, "⚠️ Скриншот не делаю — ссылка опасна.")

@bot.message_handler(commands=['check'])
def check_command(m):
    try:
        parts = m.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.send_message(m.chat.id, "❌ Укажи ссылку.\nПример: /check https://google.com", reply_markup=main_keyboard())
            return
        # Имитируем вызов check_url
        class FakeMessage:
            def __init__(self, chat_id, text):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.text = text
        fake = FakeMessage(m.chat.id, parts[1])
        check_url(fake)
    except Exception as e:
        bot.send_message(m.chat.id, f"❌ Ошибка: {e}", reply_markup=main_keyboard())

# ========== ЗАПУСК ==========
print("🚀 REVERS бот запущен")
print(f"👑 Админ ID: {ADMIN_ID}")
print(f"📊 База данных: users.db")
bot.infinity_polling()
