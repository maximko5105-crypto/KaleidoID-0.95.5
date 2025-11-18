#!/usr/bin/env python3
"""
Главный модуль KaleidoID - стабильная версия
"""

import tkinter as tk
import logging
import os
import sys
import traceback
from datetime import datetime

class SafePrinter:
    """Безопасный принтер для избежания ошибок кодировки"""
    @staticmethod
    def print(message):
        try:
            print(message)
        except (UnicodeEncodeError, IOError):
            try:
                print(message.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore'))
            except:
                pass

def get_base_path():
    """Получение базового пути"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def setup_logging():
    """Настройка логирования"""
    base_dir = get_base_path()
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f'kaleidoid_{datetime.now().strftime("%Y%m%d")}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def check_dependencies():
    """Проверка зависимостей"""
    SafePrinter.print("\n🔍 Проверка зависимостей...")
    
    dependencies = [
        ('cv2', 'opencv-python'),
        ('mediapipe', 'mediapipe'),
        ('PIL', 'Pillow'), 
        ('numpy', 'numpy')
    ]
    
    all_ok = True
    for lib, package in dependencies:
        try:
            if lib == 'PIL':
                __import__('PIL.Image')
            else:
                __import__(lib)
            SafePrinter.print(f"✅ {package}")
        except ImportError as e:
            SafePrinter.print(f"❌ {package} - {e}")
            all_ok = False
    
    return all_ok

def create_directories():
    """Создание необходимых директорий"""
    base_dir = get_base_path()
    directories = [
        os.path.join(base_dir, "data"),
        os.path.join(base_dir, "data", "exports"),
        os.path.join(base_dir, "data", "backups"),
        os.path.join(base_dir, "logs")
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        SafePrinter.print(f"📁 Создана: {os.path.basename(directory)}")

def setup_environment():
    """Настройка окружения"""
    base_dir = get_base_path()
    src_path = os.path.join(base_dir, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    SafePrinter.print(f"🏠 Рабочая директория: {base_dir}")

def initialize_database():
    """Инициализация базы данных"""
    try:
        # Динамический импорт для избежания циклических зависимостей
        from src.database.face_database import KaleidoDatabase
        
        base_dir = get_base_path()
        db_path = os.path.join(base_dir, "data", "face_database.db")
        database = KaleidoDatabase(db_path=db_path)
        
        SafePrinter.print("✅ База данных инициализирована")
        return database
        
    except Exception as e:
        SafePrinter.print(f"❌ Ошибка БД: {e}")
        traceback.print_exc()
        return None

def initialize_recognizer(database):
    """Инициализация распознавателя"""
    try:
        from src.recognition.face_recognizer import FaceRecognizer
        
        # Получаем настройки с обработкой ошибок
        min_confidence = 0.5
        if database:
            try:
                setting = database.get_setting('min_detection_confidence', '0.5')
                min_confidence = float(setting)
            except (ValueError, TypeError) as e:
                SafePrinter.print(f"⚠️ Ошибка чтения настроек: {e}, используются значения по умолчанию")
        
        recognizer = FaceRecognizer(min_detection_confidence=min_confidence)
        
        # Загружаем эмбеддинги если база существует
        if database:
            SafePrinter.print("📥 Загрузка эмбеддингов...")
            try:
                loaded_count = recognizer.load_embeddings_from_database(database)
                SafePrinter.print(f"✅ Загружено эмбеддингов: {loaded_count}")
                
                # Устанавливаем порог распознавания
                threshold_setting = database.get_setting('recognition_threshold', '0.75')
                threshold = float(threshold_setting)
                recognizer.set_recognition_threshold(threshold)
            except Exception as e:
                SafePrinter.print(f"⚠️ Не удалось загрузить эмбеддинги: {e}")
        
        SafePrinter.print("✅ Распознаватель инициализирован")
        return recognizer
        
    except Exception as e:
        SafePrinter.print(f"❌ Ошибка распознавателя: {e}")
        traceback.print_exc()
        return None

def check_camera():
    """Проверка доступности камеры"""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:
                SafePrinter.print("✅ Камера доступна")
                return True
        
        SafePrinter.print("❌ Камера недоступна")
        return False
    except Exception as e:
        SafePrinter.print(f"⚠️ Ошибка проверки камеры: {e}")
        return False

def show_error_dialog(message):
    """Показать диалог ошибки"""
    try:
        root = tk.Tk()
        root.withdraw()  # Скрыть главное окно
        from tkinter import messagebox
        messagebox.showerror("KaleidoID - Ошибка", message)
        root.destroy()
    except:
        SafePrinter.print(f"Ошибка: {message}")

def main():
    """Главная функция"""
    SafePrinter.print("\n" + "="*50)
    SafePrinter.print("🔮 KaleidoID - Face Recognition System")
    SafePrinter.print("="*50)
    
    try:
        # Настройка окружения
        setup_environment()
        create_directories()
        logger = setup_logging()
        
        # Проверка зависимостей
        if not check_dependencies():
            show_error_dialog(
                "Не все зависимости установлены!\n\n"
                "Запустите:\n"
                "python reinstall_dependencies.py\n\n"
                "Или установите вручную:\n"
                "pip install opencv-python mediapipe Pillow numpy"
            )
            return
        
        # Проверка камеры
        camera_available = check_camera()
        if not camera_available:
            SafePrinter.print("⚠️  Предупреждение: камера недоступна")
        
        # Инициализация компонентов
        SafePrinter.print("\n🔧 Инициализация компонентов...")
        
        database = initialize_database()
        if not database:
            show_error_dialog("Не удалось инициализировать базу данных")
            return
        
        recognizer = initialize_recognizer(database)
        if not recognizer:
            show_error_dialog("Не удалось инициализировать распознаватель")
            return
        
        # Запуск GUI
        SafePrinter.print("\n🎨 Запуск интерфейса...")
        
        from src.gui.main_window import KaleidoIDGUI
        
        root = tk.Tk()
        root.title("KaleidoID - Advanced Face Recognition")
        root.geometry("1200x800")
        
        # Создаем приложение
        app = KaleidoIDGUI(root, database, recognizer)
        
        # Настраиваем обработчик закрытия
        def on_closing():
            if hasattr(app, 'on_closing'):
                app.on_closing()
            else:
                root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Центрирование окна
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f"{width}x{height}+{x}+{y}")
        
        SafePrinter.print("✅ Приложение запущено")
        SafePrinter.print("💡 Закройте окно для выхода")
        
        # Запуск главного цикла
        root.mainloop()
        
    except Exception as e:
        error_msg = f"❌ Критическая ошибка: {e}"
        SafePrinter.print(error_msg)
        traceback.print_exc()
        show_error_dialog(f"Критическая ошибка при запуске:\n\n{str(e)}")

if __name__ == "__main__":
    main()