#!/usr/bin/env python3
import os
import sys
import base64
import binascii
import codecs
import urllib.parse
import json
from colorama import Fore, Style, init

init(autoreset=True)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def banner():
    print(Fore.RED + """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     ██████╗ ███████╗██╗   ██╗███████╗██████╗ ███████╗        ║
║     ██╔══██╗██╔════╝██║   ██║██╔════╝██╔══██╗██╔════╝        ║
║     ██████╔╝█████╗  ██║   ██║█████╗  ██████╔╝███████╗        ║
║     ██╔══██╗██╔══╝  ╚██╗ ██╔╝██╔══╝  ██╔══██╗╚════██║        ║
║     ██║  ██║███████╗ ╚████╔╝ ███████╗██║  ██║███████║        ║
║     ╚═╝  ╚═╝╚══════╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝╚══════╝        ║
║                                                               ║
║           🔒 CRYPTER & OBFUSCATOR 🔒                         ║
╠═══════════════════════════════════════════════════════════════╣
║        Author: Group REVERS                                   ║
║        Version: 1.0                                           ║
╚═══════════════════════════════════════════════════════════════╝
""")
    print(Fore.CYAN + "\n[!] Инструмент только для образовательных целей.\n")

def menu():
    print(Fore.YELLOW + "═" * 55)
    print(Fore.GREEN + "  [1] Шифровать скрипт/текст")
    print(Fore.GREEN + "  [2] Дешифровать скрипт/текст")
    print(Fore.GREEN + "  [0] Выход")
    print(Fore.YELLOW + "═" * 55)

def select_cipher(mode="encrypt"):
    print(Fore.CYAN + "\nВыберите метод шифрования:")
    methods = [
        "Base64", "Hex", "ROT13", "URL-encoding",
        "Base32", "JSON escape", "Шифр Цезаря", "UTF-8 decimal",
        "XOR", "Revers"
    ]
    for i, m in enumerate(methods, 1):
        print(Fore.YELLOW + f"  {i}. {m}")
    
    if mode == "decrypt":
        print(Fore.YELLOW + "  0. Автоопределение")
    
    print(Fore.YELLOW + "  q. Назад")
    
    while True:
        choice = input(Fore.GREEN + "\nВаш выбор: ").strip()
        if choice.lower() == 'q':
            return None
        if mode == "decrypt" and choice == "0":
            return "AUTO"
        if choice.isdigit() and 1 <= int(choice) <= len(methods):
            return methods[int(choice)-1]
        print(Fore.RED + "[!] Неверный выбор. Попробуйте снова.")

def get_source():
    print(Fore.CYAN + "\nВыберите источник:")
    print(Fore.YELLOW + "  1. Ввести текст вручную")
    print(Fore.YELLOW + "  2. Загрузить из файла")
    print(Fore.YELLOW + "  0. Назад")
    
    while True:
        choice = input(Fore.GREEN + "\nВаш выбор: ").strip()
        if choice == "0":
            return None, None
        if choice == "1":
            print(Fore.CYAN + "Введите текст (завершите пустой строкой):")
            lines = []
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
            return "\n".join(lines), None
        if choice == "2":
            filepath = input(Fore.CYAN + "Укажите путь к файлу: ").strip()
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        return f.read(), filepath
                except Exception as e:
                    print(Fore.RED + f"[!] Ошибка чтения файла: {e}")
            else:
                print(Fore.RED + "[!] Файл не найден.")
        else:
            print(Fore.RED + "[!] Неверный выбор.")

def encode_text(text, method):
    if method == "Base64":
        return base64.b64encode(text.encode('utf-8')).decode('utf-8')
    elif method == "Hex":
        return binascii.hexlify(text.encode('utf-8')).decode('utf-8')
    elif method == "ROT13":
        return codecs.encode(text, 'rot_13')
    elif method == "URL-encoding":
        return urllib.parse.quote(text)
    elif method == "Base32":
        return base64.b32encode(text.encode('utf-8')).decode('utf-8')
    elif method == "JSON escape":
        return json.dumps(text)[1:-1]
    elif method == "Шифр Цезаря":
        shift = 3
        result = []
        for c in text:
            if c.isupper():
                result.append(chr((ord(c) - 65 + shift) % 26 + 65))
            elif c.islower():
                result.append(chr((ord(c) - 97 + shift) % 26 + 97))
            else:
                result.append(c)
        return ''.join(result)
    elif method == "UTF-8 decimal":
        return ' '.join(str(b) for b in text.encode('utf-8'))
    elif method == "XOR":
        key = "REVERS"
        result = []
        for i, c in enumerate(text):
            result.append(chr(ord(c) ^ ord(key[i % len(key)])))
        return ''.join(result)
    elif method == "Revers":
        return text[::-1]
    else:
        return None

def decode_text(encoded, method):
    try:
        if method == "Base64":
            return base64.b64decode(encoded.encode('utf-8')).decode('utf-8')
        elif method == "Hex":
            return binascii.unhexlify(encoded.encode('utf-8')).decode('utf-8')
        elif method == "ROT13":
            return codecs.decode(encoded, 'rot_13')
        elif method == "URL-encoding":
            return urllib.parse.unquote(encoded)
        elif method == "Base32":
            return base64.b32decode(encoded.encode('utf-8')).decode('utf-8')
        elif method == "JSON escape":
            return encoded.encode('utf-8').decode('unicode_escape')
        elif method == "Шифр Цезаря":
            shift = -3
            result = []
            for c in encoded:
                if c.isupper():
                    result.append(chr((ord(c) - 65 + shift) % 26 + 65))
                elif c.islower():
                    result.append(chr((ord(c) - 97 + shift) % 26 + 97))
                else:
                    result.append(c)
            return ''.join(result)
        elif method == "UTF-8 decimal":
            return ''.join(chr(int(b)) for b in encoded.split())
        elif method == "XOR":
            key = "REVERS"
            result = []
            for i, c in enumerate(encoded):
                result.append(chr(ord(c) ^ ord(key[i % len(key)])))
            return ''.join(result)
        elif method == "Revers":
            return encoded[::-1]
        else:
            return None
    except Exception as e:
        return f"[!] Ошибка дешифрования: {e}"

def is_readable(text):
    if not text:
        return False
    printable = 0
    sample = text[:500]
    if not sample:
        return False
    for c in sample:
        if c.isprintable() or c in '\n\r\t ':
            printable += 1
    return (printable / len(sample)) > 0.7

def auto_decode(encoded):
    methods_order = [
        "Base64", "Hex", "ROT13", "URL-encoding",
        "Base32", "JSON escape", "Шифр Цезаря", "UTF-8 decimal",
        "XOR", "Revers"
    ]
    for method in methods_order:
        try:
            decoded = decode_text(encoded, method)
            if decoded and not decoded.startswith("[!] Ошибка") and is_readable(decoded):
                return method, decoded
        except:
            continue
    return None, None

def main():
    while True:
        clear_screen()
        banner()
        menu()
        choice = input(Fore.CYAN + "\nВыберите действие: ").strip()
        
        if choice == "1":
            clear_screen()
            cipher = select_cipher(mode="encrypt")
            if cipher is None:
                continue
            source_text, source_path = get_source()
            if source_text is None:
                continue
            encrypted = encode_text(source_text, cipher)
            if encrypted is None:
                print(Fore.RED + "[!] Ошибка шифрования.")
                input(Fore.CYAN + "\nНажмите Enter, чтобы продолжить...")
                continue
            
            print(Fore.GREEN + "\n[+] Зашифрованный результат:")
            print(Fore.CYAN + encrypted)
            
            save = input(Fore.CYAN + "\nСохранить результат в файл? (1 — да, 2 — нет): ").strip()
            if save == "1":
                default_name = f"encrypted_{cipher.lower().replace(' ', '_')}.txt"
                if source_path:
                    default_name = f"encrypted_{os.path.basename(source_path)}"
                out_file = input(Fore.CYAN + f"Имя файла (по умолчанию {default_name}): ").strip()
                if out_file == "":
                    out_file = default_name
                with open(out_file, "w", encoding="utf-8") as f:
                    f.write(encrypted)
                print(Fore.GREEN + f"[+] Сохранено в {out_file}")
            input(Fore.CYAN + "\nНажмите Enter, чтобы продолжить...")
            
        elif choice == "2":
            clear_screen()
            cipher = select_cipher(mode="decrypt")
            if cipher is None:
                continue
            source_text, source_path = get_source()
            if source_text is None:
                continue
            
            if cipher == "AUTO":
                method, decrypted = auto_decode(source_text)
                if method:
                    print(Fore.GREEN + f"\n[+] Автоопределённый метод: {method}")
                else:
                    print(Fore.RED + "\n[!] Не удалось определить метод дешифрования.")
                    input(Fore.CYAN + "\nНажмите Enter, чтобы продолжить...")
                    continue
            else:
                decrypted = decode_text(source_text, cipher)
                method = cipher
            
            if decrypted is None or (isinstance(decrypted, str) and decrypted.startswith("[!] Ошибка")):
                print(Fore.RED + "\n[!] Ошибка дешифрования.")
                input(Fore.CYAN + "\nНажмите Enter, чтобы продолжить...")
                continue
            
            print(Fore.GREEN + f"\n[+] Дешифрованный результат ({method}):")
            print(Fore.CYAN + decrypted)
            
            save = input(Fore.CYAN + "\nСохранить результат в файл? (1 — да, 2 — нет): ").strip()
            if save == "1":
                default_name = f"decrypted_{method.lower().replace(' ', '_')}.txt"
                if source_path:
                    default_name = f"decrypted_{os.path.basename(source_path)}"
                out_file = input(Fore.CYAN + f"Имя файла (по умолчанию {default_name}): ").strip()
                if out_file == "":
                    out_file = default_name
                with open(out_file, "w", encoding="utf-8") as f:
                    f.write(decrypted)
                print(Fore.GREEN + f"[+] Сохранено в {out_file}")
            input(Fore.CYAN + "\nНажмите Enter, чтобы продолжить...")
            
        elif choice == "0":
            clear_screen()
            print(Fore.RED + "\n[!] Выход. Береги себя и свой код.\n")
            break
        else:
            print(Fore.RED + "\n[!] Неверный выбор.\n")
            input(Fore.CYAN + "Нажмите Enter, чтобы продолжить...")

if __name__ == "__main__":
    main()
