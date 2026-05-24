# -------------------------------------------------
# KRAKEN v3.0 FINAL — модуль добавлен в BLEK-ROOM
# -------------------------------------------------

import requests
import json
import os
import sys
import time
import re
import csv
import sqlite3
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Пути к локальным базам
KRAKEN_DB_DIR = os.path.join(DATA_DIR, "db")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Accept": "*/*",
}

# -------------------------------------------------
# УТИЛИТЫ
# -------------------------------------------------

def print_kraken_banner(target, target_type):
    """Баннер модуля"""
    print(f"\n{C_WARNING}  ══════════════════════════════════════════{C_RESET}")
    print(f"{C_WARNING}         🐙 KRAKEN OSINT v3.0{C_RESET}")
    print(f"{C_WARNING}         Тип: {target_type.upper()}{C_RESET}")
    print(f"{C_WARNING}         Цель: {C_BRIGHT}{target}{C_RESET}")
    print(f"{C_WARNING}  ══════════════════════════════════════════{C_RESET}\n")

def print_section(title):
    """Заголовок секции"""
    print(f"\n {C_BRIGHT}[{title}]{C_RESET}")

def print_field(key, value, prefix="  ├─"):
    """Одно поле"""
    print(f" {prefix} {key}: {value}")

def detect_format(filepath):
    """Определить формат файла"""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".json":
        return "json"
    elif ext == ".csv":
        return "csv"
    elif ext in [".db", ".sqlite", ".sqlite3"]:
        return "sqlite"
    return None

def load_json_db(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def load_csv_db(filepath):
    data = {}
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row.get("username") or row.get("nick") or row.get("email") or str(len(data))
            data[key] = row
    return data

def load_sqlite_db(filepath):
    data = {}
    conn = sqlite3.connect(filepath)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in c.fetchall()]
    for table in tables:
        try:
            c.execute(f"SELECT * FROM {table}")
            rows = c.fetchall()
            cols = [desc[0] for desc in c.description]
            for row in rows:
                row_dict = dict(zip(cols, row))
                key = row_dict.get("username") or row_dict.get("nick") or row_dict.get("email") or row_dict.get("phone") or str(row[0])
                data[key] = row_dict
        except:
            pass
    conn.close()
    return data

def search_in_data(target, data):
    """Рекурсивный поиск target в любом формате данных"""
    target_lower = target.lower()
    results = {}
    for key, value in data.items():
        if isinstance(value, dict):
            if target_lower in str(key).lower():
                results[key] = value
            for subkey, subval in value.items():
                if target_lower in str(subval).lower():
                    results[key] = value
                    break
        elif isinstance(value, list):
            for item in value:
                if target_lower in str(item).lower():
                    results[key] = value
                    break
        else:
            if target_lower in str(value).lower() or target_lower in str(key).lower():
                results[key] = value
    return results

# -------------------------------------------------
# ОНЛАЙН-ИСТОЧНИКИ
# -------------------------------------------------

def check_holehe(email):
    """Holehe: проверка email на 120+ сервисах"""
    results = {}
    try:
        proc = subprocess.run(
            ["holehe", email, "--only-used"],
            capture_output=True, text=True, timeout=30
        )
        for line in proc.stdout.split("\n"):
            if "[+]" in line:
                service = line.strip().replace("[+] ", "")
                results[service] = True
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return results

def check_hibp(email):
    """Have I Been Pwned"""
    breaches = []
    try:
        resp = requests.get(
            f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}",
            headers={"User-Agent": "KRAKEN", "hibp-api-key": ""},
            timeout=10
        )
        if resp.status_code == 200:
            for b in resp.json():
                breaches.append({
                    "name": b.get("Name", ""),
                    "date": b.get("BreachDate", ""),
                    "data": b.get("DataClasses", []),
                })
    except:
        pass
    return breaches

def check_phoneinfoga(phone):
    """PhoneInfoga"""
    info = {}
    try:
        proc = subprocess.run(
            ["phoneinfoga", "scan", "-n", phone],
            capture_output=True, text=True, timeout=30
        )
        info["raw"] = proc.stdout[:500]
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return info

def check_emailrep(email):
    """EmailRep.io"""
    info = {}
    try:
        resp = requests.get(
            f"https://emailrep.io/{email}",
            headers={"User-Agent": "KRAKEN"},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            info["reputation"] = data.get("reputation", "unknown")
            info["suspicious"] = data.get("suspicious", False)
            info["details"] = data.get("details", {})
    except:
        pass
    return info

def check_whatsmyname(username):
    """Парсинг WhatsMyName (веб-сервис)"""
    results = {}
    try:
        resp = requests.get(
            f"https://whatsmyname.app/?q={username}",
            headers=HEADERS,
            timeout=15
        )
        if resp.status_code == 200:
            # Простой парсинг ссылок
            links = re.findall(r'https?://[^\s"\']+', resp.text)
            for link in links:
                if username.lower() in link.lower():
                    domain = re.findall(r'https?://(?:www\.)?([^/]+)', link)
                    if domain:
                        results[domain[0]] = link
    except:
        pass
    return results

def check_social_searcher(username):
    """Парсинг Social-Searcher"""
    results = {}
    try:
        resp = requests.get(
            f"https://www.social-searcher.com/social-buzz/search?q={username}",
            headers=HEADERS,
            timeout=15
        )
        if resp.status_code == 200:
            links = re.findall(r'https?://[^\s"\']+', resp.text)
            for link in links:
                if username.lower() in link.lower():
                    results[f"social_{len(results)}"] = link
    except:
        pass
    return results

# -------------------------------------------------
# ЗАГРУЗКА СВОИХ БАЗ
# -------------------------------------------------

loaded_dbs = {}  # Хранилище загруженных баз в памяти

def db_load(args):
    """Загрузить свою базу данных"""
    if not args:
        print(f"{C_ERROR}[X] Использование: db-load <путь> [--ram]{C_RESET}")
        print(f"  --ram  : загрузить только в память (не копировать на диск)")
        return
    
    filepath = args[0]
    ram_only = "--ram" in args
    
    if not os.path.exists(filepath):
        print(f"{C_ERROR}[X] Файл не найден: {filepath}{C_RESET}")
        return
    
    fmt = detect_format(filepath)
    if not fmt:
        print(f"{C_ERROR}[X] Неподдерживаемый формат. Используйте JSON, CSV, SQLite.{C_RESET}")
        return
    
    print(f"{C_INFO}[*] Загрузка базы ({fmt.upper()}): {filepath}{C_RESET}")
    
    try:
        if fmt == "json":
            data = load_json_db(filepath)
        elif fmt == "csv":
            data = load_csv_db(filepath)
        elif fmt == "sqlite":
            data = load_sqlite_db(filepath)
        
        if not ram_only:
            dest = os.path.join(KRAKEN_DB_DIR, os.path.basename(filepath))
            os.makedirs(KRAKEN_DB_DIR, exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            print(f"{C_SUCCESS}[OK] База сохранена: {dest}{C_RESET}")
        
        # Держим в памяти
        loaded_dbs[filepath] = data
        print(f"{C_SUCCESS}[OK] База загружена в память. Записей: {len(data)}{C_RESET}")
        
    except Exception as e:
        print(f"{C_ERROR}[X] Ошибка загрузки: {e}{C_RESET}")

# -------------------------------------------------
# ГЛАВНАЯ ФУНКЦИЯ
# -------------------------------------------------

def run_kraken(args):
    """🐙 KRAKEN — Полный цифровой профиль"""
    
    if not args:
        print(f"\n{C_ERROR}[X] Использование: kraken <цель>{C_RESET}")
        print(f"{C_DIM}  Пример: kraken mr.robot{C_RESET}")
        print(f"{C_DIM}  Пример: kraken user@email.com{C_RESET}")
        print(f"{C_DIM}  Пример: kraken +79001234567{C_RESET}\n")
        return
    
    target = args[0]
    
    # Определяем тип цели
    if "@" in target:
        target_type = "email"
    elif target.replace("+", "").replace("-", "").replace(" ", "").isdigit():
        target_type = "phone"
    else:
        target_type = "username"
    
    print_kraken_banner(target, target_type)
    
    # ---------- ЭТАП 1: СВОИ БАЗЫ ----------
    print(f"{C_INFO}[*] ЭТАП 1: Поиск в загруженных базах...{C_RESET}")
    
    all_local_results = {}
    for filepath, data in loaded_dbs.items():
        found = search_in_data(target, data)
        if found:
            basename = os.path.basename(filepath)
            all_local_results[basename] = found
            print(f"  {C_SUCCESS}[+]{C_RESET} {basename}: найдено {len(found)} записей")
    
    if not all_local_results:
        print(f"  {C_DIM}[~]{C_RESET} Загруженных баз нет. Используйте db-load для загрузки.")
    
    # ---------- ЭТАП 2: ОНЛАЙН-ИСТОЧНИКИ ----------
    print(f"\n{C_INFO}[*] ЭТАП 2: Онлайн-источники...{C_RESET}")
    
    holehe_results = {}
    hibp_results = []
    phoneinfoga_results = {}
    emailrep_results = {}
    whatsmyname_results = {}
    social_searcher_results = {}
    
    if target_type == "email":
        print(f"  {C_DIM}[~]{C_RESET} Запуск Holehe...")
        holehe_results = check_holehe(target)
        print(f"  {C_SUCCESS}[+]{C_RESET} Holehe: найдено {len(holehe_results)} сервисов")
        
        print(f"  {C_DIM}[~]{C_RESET} Проверка HIBP...")
        hibp_results = check_hibp(target)
        print(f"  {C_SUCCESS}[+]{C_RESET} HIBP: {len(hibp_results)} утечек")
        
        print(f"  {C_DIM}[~]{C_RESET} EmailRep...")
        emailrep_results = check_emailrep(target)
        print(f"  {C_SUCCESS}[+]{C_RESET} EmailRep: получен")
    
    if target_type == "phone":
        print(f"  {C_DIM}[~]{C_RESET} PhoneInfoga...")
        phoneinfoga_results = check_phoneinfoga(target)
        print(f"  {C_SUCCESS}[+]{C_RESET} PhoneInfoga: завершён")
    
    if target_type == "username" or target_type == "email":
        print(f"  {C_DIM}[~]{C_RESET} WhatsMyName...")
        whatsmyname_results = check_whatsmyname(target)
        print(f"  {C_SUCCESS}[+]{C_RESET} WhatsMyName: {len(whatsmyname_results)} ссылок")
        
        print(f"  {C_DIM}[~]{C_RESET} Social-Searcher...")
        social_searcher_results = check_social_searcher(target)
        print(f"  {C_SUCCESS}[+]{C_RESET} Social-Searcher: {len(social_searcher_results)} результатов")
    
    # ---------- ВЫВОД ОТЧЁТА ----------
    print(f"\n{C_WARNING}═══════════════════════════════════════════════════════════{C_RESET}")
    print(f"{C_WARNING}                   🐙 KRAKEN REPORT{C_RESET}")
    print(f"{C_WARNING}                Цель: {target}{C_RESET}")
    print(f"{C_WARNING}═══════════════════════════════════════════════════════════{C_RESET}")
    
    # Локальные базы
    if all_local_results:
        print_section("📂 ЛОКАЛЬНЫЕ БАЗЫ")
        for basename, results in all_local_results.items():
            print(f"\n  {C_BRIGHT}{basename}:{C_RESET}")
            for key, value in list(results.items())[:10]:
                if isinstance(value, dict):
                    print(f"  ├─ {key}:")
                    for k, v in value.items():
                        if v and str(v).strip():
                            print(f"  │  └─ {k}: {v}")
                else:
                    print(f"  ├─ {key}: {value}")
    
    # Holehe
    if holehe_results:
        print_section("📧 HOLEHE (EMAIL НА СЕРВИСАХ)")
        for service in list(holehe_results.keys())[:20]:
            print(f"  ├─ {service}")
    
    # HIBP
    if hibp_results:
        print_section("⚠️ УТЕЧКИ (HAVE I BEEN PWNED)")
        for br in hibp_results:
            print(f"  ├─ {br['name']} ({br['date']})")
            print(f"  │  Данные: {', '.join(br.get('data', []))}")
    
    # EmailRep
    if emailrep_results:
        print_section("🔍 РЕПУТАЦИЯ EMAIL")
        print(f"  ├─ Репутация: {emailrep_results.get('reputation', '—')}")
        print(f"  ├─ Подозрительный: {emailrep_results.get('suspicious', '—')}")
    
    # PhoneInfoga
    if phoneinfoga_results:
        print_section("📞 PHONEINFOGA")
        raw = phoneinfoga_results.get("raw", "")
        for line in raw.split("\n")[:15]:
            if line.strip():
                print(f"  ├─ {line.strip()}")
    
    # WhatsMyName
    if whatsmyname_results:
        print_section("🌐 WHATSMYNAME")
        for domain, url in list(whatsmyname_results.items())[:15]:
            print(f"  ├─ {domain}")
    
    # Social-Searcher
    if social_searcher_results:
        print_section("🔎 SOCIAL-SEARCHER")
        for key, url in list(social_searcher_results.items())[:10]:
            print(f"  ├─ {url}")
    
    # Если ничего не найдено
    if not any([all_local_results, holehe_results, hibp_results, emailrep_results,
                phoneinfoga_results, whatsmyname_results, social_searcher_results]):
        print(f"\n  {C_ERROR}[!] Ничего не найдено.{C_RESET}")
    
    print(f"\n{C_WARNING}═══════════════════════════════════════════════════════════{C_RESET}")
    print(f"{C_ERROR}[!] Сохрани себе отдельно, если информация ещё нужна будет.{C_RESET}")
    print(f"{C_WARNING}═══════════════════════════════════════════════════════════{C_RESET}\n")