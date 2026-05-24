#!/usr/bin/env python3
"""
BLEK-ROOM v2.0 — Эмулятор операционной системы
Разработчик: MRX
"""
import os
import sys
import time
import getpass
import hashlib
import sqlite3
import json
import subprocess
import tempfile
import socket
import zipfile
import platform
from colorama import Fore, Style, init

init(autoreset=True)

# -------------------------------------------------
# КОНСТАНТЫ
# -------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

PASSWORD_FILE = os.path.join(DATA_DIR, "password.hash")
HISTORY_DB   = os.path.join(DATA_DIR, "history.db")
CONFIG_FILE  = os.path.join(DATA_DIR, "config.json")

C_ERROR   = Fore.RED
C_SUCCESS = Fore.GREEN
C_WARNING = Fore.YELLOW
C_INFO    = Fore.LIGHTCYAN_EX
C_PROMPT  = Fore.LIGHTRED_EX
C_DIM     = Fore.LIGHTBLACK_EX
C_BRIGHT  = Fore.LIGHTWHITE_EX
C_RESET   = Style.RESET_ALL

# -------------------------------------------------
# ПАРОЛЬ
# -------------------------------------------------
def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def is_first_launch():
    return not os.path.exists(PASSWORD_FILE)

def set_password():
    print(f"\n{C_WARNING}[FIRST LAUNCH DETECTED]{C_RESET}")
    print("Установите пароль для доступа к BLEK-ROOM.\n")
    while True:
        pwd1 = getpass.getpass("Придумайте пароль: ")
        pwd2 = getpass.getpass("Повторите пароль: ")
        if pwd1 == pwd2:
            if len(pwd1) < 4:
                print(f"{C_ERROR}Пароль должен быть не короче 4 символов.{C_RESET}\n")
                continue
            with open(PASSWORD_FILE, "w") as f:
                f.write(hash_password(pwd1))
            print(f"\n{C_WARNING}[!] Пароль сохранён. НЕ ЗАБУДЬТЕ ЕГО!{C_RESET}")
            input("\nНажмите Enter, чтобы продолжить...")
            return True
        else:
            print(f"{C_ERROR}Пароли не совпадают.{C_RESET}\n")

def check_password():
    print(f"\n{C_INFO}[SYSTEM] Доступ к BLEK-ROOM требует авторизации.{C_RESET}\n")
    for attempt in range(3):
        pwd = getpass.getpass("Введите пароль: ")
        hashed_input = hash_password(pwd)
        with open(PASSWORD_FILE, "r") as f:
            stored_hash = f.read().strip()
        if hashed_input == stored_hash:
            print(f"{C_SUCCESS}[ACCESS GRANTED]{C_RESET}\n")
            return True
        else:
            left = 2 - attempt
            print(f"{C_ERROR}[ACCESS DENIED] Осталось попыток: {left}{C_RESET}\n")
    print(f"{C_ERROR}[SYSTEM] Превышено количество попыток. Выход.{C_RESET}")
    return False

# -------------------------------------------------
# БАЗА ДАННЫХ (ИСТОРИЯ)
# -------------------------------------------------
def init_db():
    conn = sqlite3.connect(HISTORY_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  command TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def add_to_history(cmd):
    conn = sqlite3.connect(HISTORY_DB)
    c = conn.cursor()
    c.execute("INSERT INTO history (command) VALUES (?)", (cmd,))
    conn.commit()
    conn.close()

def show_history():
    conn = sqlite3.connect(HISTORY_DB)
    c = conn.cursor()
    c.execute("SELECT command, timestamp FROM history ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    for cmd, ts in rows:
        print(f"{C_DIM}{ts}{C_RESET} -> {C_BRIGHT}{cmd}{C_RESET}")
    conn.close()

# -------------------------------------------------
# КОНФИГ
# -------------------------------------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    else:
        default = {"theme": "red"}
        with open(CONFIG_FILE, "w") as f:
            json.dump(default, f)
        return default

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

# -------------------------------------------------
# АНИМАЦИЯ ЗАПУСКА
# -------------------------------------------------

def beep():
    """Звуковой сигнал"""
    sys.stdout.write('\a')
    sys.stdout.flush()

def slow_print(text, delay=0.01):
    """Медленная печать"""
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def progress_bar():
    """Прогресс-бар загрузки модулей"""
    modules = [
        ("[CORE]", "Загрузка ядра BLEK", 0.15),
        ("[AUTH]", "Инициализация протоколов безопасности", 0.1),
        ("[DB]", "Подключение базы данных истории", 0.08),
        ("[ENV]", "Сканирование окружения", 0.12),
        ("[SYS]", "Монтирование файловой системы", 0.2),
        ("[NET]", "Проверка сетевых интерфейсов", 0.1),
        ("[DONE]", "Все модули загружены", 0.05),
    ]

    print(f"\n{C_INFO}[SYSTEM] Запуск BLEK-ROOM...{C_RESET}\n")
    
    for tag, desc, delay in modules:
        sys.stdout.write(f"  {C_DIM}{tag}{C_RESET} {desc} ")
        sys.stdout.flush()
        for dot in range(3):
            time.sleep(0.1)
            sys.stdout.write(".")
            sys.stdout.flush()
        time.sleep(delay)
        sys.stdout.write(f" {C_SUCCESS}[OK]{C_RESET}\n")
        sys.stdout.flush()
    
    beep()
    print(f"\n{C_WARNING}[!] ДОСТУП РАЗРЕШЁН. ДОБРО ПОЖАЛОВАТЬ.{C_RESET}")
    time.sleep(1.5)

def show_banner():
    """ASCII-арт REVERS из ANLOK"""
    art = f"""
{Fore.RED}
⣸⠒⠠⢀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⡇⠀⠀⠀⠑⠄⡀⠀⠀⠀⣀⠀⠀⠀
⠃⠀⠀⠀⠀⠀⢈⣵⣦⢸⣿⡧⠀⠀
⠀⠀⠀⠀⠀⠀⣼⣿⣿⣾⢏⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢿⣼⣿⢟⣷⣷⣆⠀
⠀⠀⠀⠀⠀⠀⣾⣿⣿⣿⣿⡿⠈⢆
⠀⠀⠀⠀⠀⢰⢸⣿⣿⣿⣿⠇⠀⠈
⠀⠀⠀⠀⠀⢸⢸⣿⣿⣿⡇⠀⠀⠀
⠀⠀⠀⠀⠀⡈⣼⣿⣿⣿⡇⠀⠀⠀
⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⡇⠀⠀⠀
⠀⠀⠀⠀⣸⣿⣿⣿⣿⣿⣿⠀⠀⠀
⠀⠀⠀⠾⢿⣿⣿⠿⠿⣿⡿⠀⠀⠀

{C_WARNING}           BLEK-ROOM v2.0
   К вашим услугам{C_RESET}
"""
    # Быстрый вывод арта (не медленный)
    print(art)

def full_banner():
    """Полная заставка при запуске"""
    os.system('clear' if os.name == 'posix' else 'cls')
    progress_bar()
    show_banner()
    print(f"{C_DIM}Введите 'help' для списка команд.{C_RESET}\n")

# -------------------------------------------------
# КОМАНДЫ
# -------------------------------------------------

def edit_file(args):
    """Редактирование файла в nano"""
    if not args:
        print(f"{C_ERROR}Использование: edit <файл>{C_RESET}")
        return
    filename = args[0]
    if not os.path.exists(filename):
        open(filename, 'w').close()
        print(f"{C_SUCCESS}Создан новый файл: {filename}{C_RESET}")
    subprocess.call(['nano', '-w', filename])
    print(f"{C_INFO}Редактор закрыт.{C_RESET}")

def unpack_archive(args):
    """Распаковка архива"""
    if not args:
        print(f"{C_ERROR}Использование: unpack <архив> [папка]{C_RESET}")
        return
    archive = args[0]
    if not os.path.exists(archive):
        print(f"{C_ERROR}Архив не найден.{C_RESET}")
        return
    extract_dir = args[1] if len(args) > 1 else os.path.splitext(archive)[0]
    try:
        with zipfile.ZipFile(archive, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            print(f"{C_SUCCESS}Распаковано в {extract_dir}{C_RESET}")
    except Exception as e:
        print(f"{C_ERROR}Ошибка распаковки: {e}{C_RESET}")

def run_script(args):
    """Запуск Python-скрипта"""
    if not args:
        print(f"{C_ERROR}Использование: run <script.py>{C_RESET}")
        return
    script = args[0]
    if not os.path.exists(script) or not script.endswith('.py'):
        print(f"{C_ERROR}Файл не найден или не является Python-скриптом.{C_RESET}")
        return
    print(f"{C_INFO}Запуск {script}...{C_RESET}")
    subprocess.run([sys.executable, script])

def sandbox_exec(args):
    """Выполнение в песочнице (временная папка)"""
    if not args:
        print(f"{C_ERROR}Использование: sandbox <команда>{C_RESET}")
        return
    command = ' '.join(args)
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"{C_INFO}Выполнение в песочнице: {tmpdir}{C_RESET}")
        try:
            result = subprocess.run(command, shell=True, cwd=tmpdir,
                                    capture_output=True, text=True, timeout=5)
            print(f"{C_BRIGHT}STDOUT:{C_RESET}", result.stdout)
            if result.stderr:
                print(f"{C_ERROR}STDERR:{C_RESET}", result.stderr)
        except subprocess.TimeoutExpired:
            print(f"{C_ERROR}Команда превысила лимит времени (5 с).{C_RESET}")
        except Exception as e:
            print(f"{C_ERROR}Ошибка: {e}{C_RESET}")

def show_env():
    """Информация о системе"""
    print(f"{C_BRIGHT}OS:{C_RESET} {platform.system()} {platform.release()}")
    print(f"{C_BRIGHT}Python:{C_RESET} {sys.version}")
    print(f"{C_BRIGHT}Рабочая папка:{C_RESET} {os.getcwd()}")
    try:
        import psutil
        mem = psutil.virtual_memory()
        print(f"{C_BRIGHT}RAM:{C_RESET} {mem.total // (1024**3)} GB total, {mem.percent}% used")
        cpu = psutil.cpu_percent()
        print(f"{C_BRIGHT}CPU:{C_RESET} {cpu}%")
    except ImportError:
        print(f"{C_DIM}(Для детальной информации: pip install psutil){C_RESET}")

def scan_ports(args):
    """Сканирование портов"""
    target = args[0] if args else "127.0.0.1"
    ports = [21, 22, 23, 80, 443, 8080, 3306, 5432, 6379, 27017]
    print(f"{C_INFO}Сканирование {target}...{C_RESET}\n")
    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex((target, port))
        if result == 0:
            print(f"  {C_SUCCESS}[OPEN]{C_RESET}   Порт {port}")
        else:
            print(f"  {C_ERROR}[CLOSED]{C_RESET} Порт {port}")
        sock.close()

def change_theme(args):
    """Смена темы"""
    if not args:
        print(f"{C_ERROR}Использование: theme [red|green]{C_RESET}")
        return
    new_theme = args[0]
    if new_theme not in ["red", "green"]:
        print(f"{C_ERROR}Доступные темы: red, green{C_RESET}")
        return
    config = load_config()
    config["theme"] = new_theme
    save_config(config)
    print(f"{C_WARNING}Тема изменена на {new_theme}. Перезапустите BLEK-ROOM.{C_RESET}")

def show_help():
    """Помощь"""
    help_text = f"""
{C_WARNING}================================================
              BLEK-ROOM v2.0
================================================{C_RESET}

{C_INFO}Доступные команды:{C_RESET}
  {C_BRIGHT}help{C_RESET}      - показать эту справку
  {C_BRIGHT}clear{C_RESET}     - очистить экран и показать баннер
  {C_BRIGHT}exit{C_RESET}      - выйти из BLEK-ROOM
  {C_BRIGHT}edit{C_RESET}      - редактировать файл (nano)
  {C_BRIGHT}unpack{C_RESET}    - распаковать архив (.zip)
  {C_BRIGHT}run{C_RESET}       - запустить Python-скрипт
  {C_BRIGHT}sandbox{C_RESET}   - выполнить команду в песочнице
  {C_BRIGHT}env{C_RESET}       - информация о системе
  {C_BRIGHT}history{C_RESET}   - история команд
  {C_BRIGHT}theme{C_RESET}     - сменить тему (red/green)
  {C_BRIGHT}scan{C_RESET}      - сканировать порты

{C_DIM}Разработчик: MRX{C_RESET}
"""
    print(help_text)

# -------------------------------------------------
# ОБРАБОТЧИК КОМАНД
# -------------------------------------------------

def execute_command(cmd):
    parts = cmd.split()
    if not parts:
        return
    command = parts[0]
    args = parts[1:]

    if command == "help":
        show_help()
    elif command == "clear":
        os.system('clear' if os.name == 'posix' else 'cls')
        show_banner()
    elif command == "exit":
        print(f"{C_WARNING}[SYSTEM] Завершение работы BLEK-ROOM...{C_RESET}")
        sys.exit(0)
    elif command == "edit":
        edit_file(args)
    elif command == "unpack":
        unpack_archive(args)
    elif command == "run":
        run_script(args)
    elif command == "sandbox":
        sandbox_exec(args)
    elif command == "env":
        show_env()
    elif command == "history":
        show_history()
    elif command == "theme":
        change_theme(args)
    elif command == "scan":
        scan_ports(args)
    else:
        print(f"{C_ERROR}[!] Неизвестная команда: {command}{C_RESET}")
        print(f"{C_DIM}Введите 'help' для списка команд.{C_RESET}")

# -------------------------------------------------
# ГЛАВНЫЙ ЦИКЛ
# -------------------------------------------------

def main():
    # Авторизация
    if is_first_launch():
        set_password()
    if not check_password():
        sys.exit(1)

    # Инициализация
    init_db()
    load_config()

    # Заставка
    full_banner()

    # Главный цикл
    while True:
        try:
            cmd = input(f"\n{C_PROMPT}blek>{C_RESET} ").strip()
            if cmd:
                add_to_history(cmd)
            execute_command(cmd)
        except KeyboardInterrupt:
            print(f"\n{C_WARNING}[SYSTEM] Прерывание. Выход...{C_RESET}")
            sys.exit(0)
        except Exception as e:
            print(f"{C_ERROR}[ERROR] {e}{C_RESET}")

if __name__ == "__main__":
    main()