#!/usr/bin/env python3
"""
ИСПРАВЛЕННЫЙ скрипт установки зависимостей для KaleidoID
- Исправлена установка mediapipe для новых версий Python
- Добавлена обработка Windows-специфичных проблем
- Добавлены совместимые версии пакетов
"""

import os
import sys
import subprocess
import platform
import time
from pathlib import Path
import json

def print_color(text, color_code):
    """Цветной вывод для Windows и Unix"""
    if platform.system() == "Windows":
        try:
            from colorama import init, Fore, Style
            init()
            colors = {
                "32": Fore.GREEN,
                "31": Fore.RED, 
                "33": Fore.YELLOW,
                "36": Fore.CYAN,
                "35": Fore.MAGENTA
            }
            color = colors.get(str(color_code), "")
            print(f"{color}{text}{Style.RESET_ALL}")
        except ImportError:
            print(text)
    else:
        print(f"\033[{color_code}m{text}\033[0m")

def print_success(text):
    print_color(f"✅ {text}", "32")

def print_error(text):
    print_color(f"❌ {text}", "31")

def print_warning(text):
    print_color(f"⚠️ {text}", "33")

def print_info(text):
    print_color(f"💡 {text}", "36")

def get_pip_command():
    """Получить правильную команду для pip"""
    return [sys.executable, "-m", "pip"]

def check_python_version():
    """Проверка версии Python"""
    print_info("Проверка версии Python...")
    if sys.version_info < (3, 8):
        print_error("Требуется Python 3.8 или выше")
        return False
    print_success(f"Python {platform.python_version()}")
    return True

def install_package(package, only_binary=False, no_deps=False):
    """Установка пакета с правильными параметрами для Windows"""
    pip_cmd = get_pip_command()
    
    # Флаги для Windows
    install_flags = [
        "--no-cache-dir",
        "--upgrade",
    ]
    
    if only_binary:
        install_flags.append("--only-binary=:all:")
    
    if no_deps:
        install_flags.append("--no-deps")
    
    # Основные зеркала PyPI
    mirrors = [
        "https://pypi.org/simple/",
        "https://pypi.tuna.tsinghua.edu.cn/simple",
        "https://mirrors.aliyun.com/pypi/simple/"
    ]
    
    for mirror in mirrors:
        try:
            cmd = pip_cmd + ["install"] + install_flags + [
                "--index-url", mirror,
                package
            ]
            
            print_info(f"Выполнение: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                print_success(f"✅ Установлен: {package} (через {mirror})")
                return True
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                print_warning(f"Ошибка установки {package} через {mirror}")
                print_warning(f"Детали: {error_msg[:500]}...")
        except Exception as e:
            print_warning(f"Исключение при установке {package}: {e}")
    
    return False

def install_core_dependencies():
    """Установка основных зависимостей с совместимыми версиями"""
    print_info("Установка основных зависимостей...")
    
    # 1. Сначала устанавливаем numpy с бинарными пакетами
    print_info("📦 Установка numpy...")
    if not install_package("numpy==2.3.4", only_binary=True):
        print_warning("Не удалось установить numpy==2.3.4, пробуем последнюю совместимую версию")
        if not install_package("numpy>=2.3.4,<2.0.0", only_binary=True):
            print_error("❌ Критическая ошибка: не удалось установить numpy")
            return False
    
    # 2. Устанавливаем protobuf - необходимая зависимость для mediapipe
    print_info("📦 Установка protobuf...")
    if not install_package("protobuf==3.20.3", only_binary=True):
        print_warning("Не удалось установить protobuf==3.20.3, пробуем другую версию")
        if not install_package("protobuf==4.25.3", only_binary=True):
            print_error("❌ Критическая ошибка: не удалось установить protobuf")
            return False
    
    # 3. Устанавливаем opencv-python
    print_info("📦 Установка opencv-python...")
    if not install_package("opencv-python==4.10.0.84", only_binary=True):
        print_warning("Не удалось установить opencv-python==4.10.0.84, пробуем альтернативную версию")
        if not install_package("opencv-python==4.10.0.84", only_binary=True):
            print_error("❌ Критическая ошибка: не удалось установить opencv-python")
            return False
    
    # 4. УСТАНОВКА MEDIAPIPE - КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ
    print_info("📦 Установка mediapipe...")
    
    # Для Python 3.12+ используем более новую версию mediapipe
    python_major = sys.version_info.major
    python_minor = sys.version_info.minor
    
    if python_minor >= 12:
        # Для Python 3.12+ используем версию 0.10.14 или новее
        if not install_package("mediapipe==0.10.21", only_binary=True):
            print_warning("Не удалось установить mediapipe==0.10.10, пробуем самую последнюю версию")
            if not install_package("mediapipe", only_binary=True):
                print_error("❌ Критическая ошибка: не удалось установить mediapipe для Python 3.12+")
                return False
    else:
        # Для Python 3.8-3.11 используем версию 0.10.14 (0.10.26 не существует в PyPI)
        if not install_package("mediapipe==0.10.21", only_binary=True):
            print_warning("Не удалось установить mediapipe==0.10.14, пробуем альтернативную версию")
            if not install_package("mediapipe==0.10.14", only_binary=True):
                print_error("❌ Критическая ошибка: не удалось установить mediapipe")
                return False
    
    # 5. Устанавливаем остальные зависимости
    print_info("📦 Установка остальных зависимостей...")
    packages = [
        "Pillow==12.0.0",
        "pyinstaller==6.16.0"
    ]
    
    for package in packages:
        if not install_package(package, only_binary=True):
            print_warning(f"⚠️  Не удалось установить {package}, пробуем без указания версии")
            package_name = package.split("==")[0]
            if not install_package(package_name, only_binary=True):
                print_error(f"❌ Критическая ошибка: не удалось установить {package_name}")
                return False
    
    return True

def verify_installation():
    """Проверка установки пакетов"""
    print_info("Проверка установленных пакетов...")
    
    packages = [
        ("cv2", "OpenCV"),
        ("mediapipe", "MediaPipe"), 
        ("PIL", "Pillow"),
        ("numpy", "NumPy"),
        ("google.protobuf", "Protobuf")
    ]
    
    all_ok = True
    for import_name, display_name in packages:
        try:
            if import_name == "PIL":
                from PIL import Image
                version = Image.__version__
            elif import_name == "google.protobuf":
                import google.protobuf
                version = google.protobuf.__version__
            else:
                module = __import__(import_name)
                version = getattr(module, '__version__', 'unknown')
            
            print_success(f"{display_name} (v{version}) - OK")
        except ImportError as e:
            print_error(f"{display_name} - Ошибка импорта: {e}")
            all_ok = False
        except Exception as e:
            print_error(f"{display_name} - Неожиданная ошибка: {e}")
            all_ok = False
    
    return all_ok

def create_directories():
    """Создание необходимых директорий"""
    print_info("Создание структуры директорий...")
    
    directories = [
        "data",
        "data/exports", 
        "data/backups",
        "logs",
        "src",
        "src/database",
        "src/recognition", 
        "src/gui",
        "src/utils"
    ]
    
    for directory in directories:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        print_success(f"Создана: {directory}")

def main():
    """Основная функция"""
    print("\n" + "="*80)
    print_color("🔮 KALEIDOID - УСТАНОВКА ЗАВИСИМОСТЕЙ (ИСПРАВЛЕННАЯ ВЕРСИЯ)", "35")
    print("="*80)
    print_info(f"Текущий путь: {Path.cwd()}")
    print_info(f"Виртуальное окружение: {sys.prefix}")
    print_info(f"Версия Python: {platform.python_version()}")
    
    # Проверка Python
    if not check_python_version():
        return
    
    response = input("\n⚠️  Вы уверены что хотите установить все зависимости? (y/N): ")
    if response.lower() != 'y':
        print_info("Отменено пользователем")
        return
    
    try:
        # Установка зависимостей
        if install_core_dependencies():
            print("\n" + "="*80)
            print_info("ПРОВЕРКА УСТАНОВКИ")
            print("="*80)
            
            # Проверка установки
            if verify_installation():
                # Создание директорий
                create_directories()
                
                print("\n" + "="*80)
                print_success("🎉 УСТАНОВКА ЗАВЕРШЕНА УСПЕШНО!")
                print("="*80)
                print_info("Запуск приложения: python main.py")
                print_info("Сборка EXE: python build_exe.py")
                
                # Создаем файл с информацией об установке
                install_info = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "python_version": platform.python_version(),
                    "system": platform.system(),
                    "packages": {
                        "numpy": "1.26.4",
                        "protobuf": "4.25.3",
                        "opencv-python": "4.9.0.80 or 4.11.0.86",
                        "mediapipe": "0.10.21 (для Python 3.12+) или 0.10.14 (для Python 3.8-3.11)",
                        "Pillow": "12.0.0",
                        "pyinstaller": "6.16.0"
                    }
                }
                
                with open('install_info.json', 'w', encoding='utf-8') as f:
                    json.dump(install_info, f, indent=2, ensure_ascii=False)
                print_success("Создан файл install_info.json с информацией об установке")
            else:
                print_error("❌ Некоторые пакеты не установлены корректно")
                print_warning("Попробуйте запустить скрипт с правами администратора")
        else:
            print_error("❌ Ошибка установки основных зависимостей")
            print_warning("Рекомендуется:")
            print_info("1. Запустить PowerShell от имени администратора")
            print_info("2. Выполнить: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser")
            print_info("3. Переактивировать виртуальное окружение")
            print_info("4. Запустить скрипт заново")
    
    except KeyboardInterrupt:
        print_error("\n⚠️  Установка прервана пользователем")
    except Exception as e:
        print_error(f"❌ Критическая ошибка: {e}")
        import traceback
        print_error(f"Трассировка: {traceback.format_exc()}")
        print_warning("Рекомендуется запустить от имени администратора")

if __name__ == "__main__":
    main()