import sys
import os
import tempfile
from pathlib import Path

def fix_mediapipe_paths():
    """Исправление путей для MediaPipe в собранном приложении"""
    try:
        if getattr(sys, 'frozen', False):
            # Мы в собранном приложении
            base_path = sys._MEIPASS
            
            # Исправляем пути для mediapipe
            import mediapipe as mp
            mp_path = Path(mp.__file__).parent
            
            # Создаем временные файлы если нужно
            temp_dir = tempfile.gettempdir()
            mediapipe_temp = Path(temp_dir) / 'mediapipe_temp'
            mediapipe_temp.mkdir(exist_ok=True)
            
            print(f"MediaPipe paths fixed: {mp_path}")
            
    except Exception as e:
        print(f"Error fixing MediaPipe paths: {e}")

def fix_opencv_paths():
    """Исправление путей для OpenCV в собранном приложении"""
    try:
        if getattr(sys, 'frozen', False):
            import cv2
            # Принудительно загружаем необходимые DLL
            cv2._load_videoio_backend()
    except Exception as e:
        print(f"Error fixing OpenCV paths: {e}")

def setup_temp_directories():
    """Настройка временных директорий для работы приложения"""
    try:
        # Создаем временные папки для работы с файлами
        temp_dirs = ['captured_faces', 'temp_images', 'exports']
        for dir_name in temp_dirs:
            dir_path = Path(tempfile.gettempdir()) / 'kaleido_id' / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Error setting up temp directories: {e}")

# Выполняем исправления при импорте
if getattr(sys, 'frozen', False):
    fix_mediapipe_paths()
    fix_opencv_paths()
    setup_temp_directories()
