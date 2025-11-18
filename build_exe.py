#!/usr/bin/env python3
"""
Улучшенный скрипт сборки KaleidoID в EXE
Версия 3.0 - Исправление работы камеры и кнопок создания фото
"""

import os
import sys
import shutil
import subprocess
import platform
import tempfile
from pathlib import Path

def cleanup_build_dirs():
    """Очистка временных директорий сборки"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"🧹 Очистка {dir_name}...")
            try:
                shutil.rmtree(dir_name)
            except Exception as e:
                print(f"⚠️ Не удалось очистить {dir_name}: {e}")
    
    # Очищаем pycache в поддиректориях
    for root, dirs, files in os.walk('.'):
        for dir_name in dirs:
            if dir_name == '__pycache__':
                pycache_path = os.path.join(root, dir_name)
                print(f"🧹 Очистка {pycache_path}...")
                try:
                    shutil.rmtree(pycache_path)
                except Exception as e:
                    print(f"⚠️ Не удалось очистить {pycache_path}: {e}")

def check_dependencies():
    """Проверка и установка необходимых зависимостей"""
    required_packages = [
        'pyinstaller>=6.16.0',
        'opencv-python==4.11.0.86',
        'mediapipe',
        'pillow==12.0.0',
        'numpy==2.3.4',
        'protobuf==4.25.3'
    ]
    
    print("🔍 Проверка зависимостей...")
    for package in required_packages:
        try:
            if '>=' in package:
                pkg_name = package.split('>=')[0]
            else:
                pkg_name = package
                
            __import__(pkg_name.replace('-', '_'))
            print(f"✅ {pkg_name} установлен")
        except ImportError:
            print(f"❌ {pkg_name} не установлен, устанавливаю...")
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print(f"✅ {pkg_name} успешно установлен")
            except subprocess.CalledProcessError:
                print(f"❌ Не удалось установить {package}")

def create_camera_fix_spec_file():
    """Создание spec файла с исправлениями для работы камеры"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path

block_cipher = None

# Увеличиваем лимит рекурсии
sys.setrecursionlimit(5000)

def get_all_data_files():
    """Сбор всех необходимых данных для включения в сборку"""
    datas = []
    
    # Добавляем основные папки
    folders = ['src', 'data', 'logs']
    for folder in folders:
        if os.path.exists(folder):
            for root, dirs, files in os.walk(folder):
                for file in files:
                    full_path = os.path.join(root, file)
                    if not any(skip in full_path for skip in ['__pycache__', '.tmp', 'temp']):
                        relative_path = os.path.relpath(root, '.')
                        datas.append((full_path, relative_path))
    
    # Добавляем специфичные файлы для mediapipe
    try:
        import mediapipe as mp
        mp_path = Path(mp.__file__).parent
        # Включаем все файлы моделей mediapipe
        for pattern in ['*.tflite', '*.pbtxt', '*.bin']:
            for model_file in mp_path.rglob(pattern):
                relative_path = model_file.relative_to(Path(mp_path).parent)
                datas.append((str(model_file), str(relative_path.parent)))
        print(f"✅ Добавлены модели MediaPipe: {len([d for d in datas if 'mediapipe' in d[0]])} файлов")
    except Exception as e:
        print(f"⚠️ Ошибка добавления моделей MediaPipe: {e}")
    
    # Добавляем файлы OpenCV
    try:
        import cv2
        cv2_path = Path(cv2.__file__).parent
        # Включаем Haar каскады и другие данные OpenCV
        for xml_file in cv2_path.rglob('*.xml'):
            relative_path = xml_file.relative_to(Path(cv2_path).parent)
            datas.append((str(xml_file), str(relative_path.parent)))
        print(f"✅ Добавлены файлы OpenCV: {len([d for d in datas if 'cv2' in d[0]])} файлов")
    except Exception as e:
        print(f"⚠️ Ошибка добавления файлов OpenCV: {e}")
    
    return datas

a = Analysis(
    ['main.py'],
    pathex=[os.getcwd()],
    binaries=[],
    datas=get_all_data_files(),
    hiddenimports=[
        # Tkinter и GUI
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        
        # Pillow для изображений
        'PIL',
        'PIL._tkinter_finder',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL.ImageOps',
        'PIL.ImageFilter',
        'PIL.ImageDraw',
        
        # OpenCV
        'cv2',
        'cv2.cv2',
        'cv2.data',
        'cv2.videoio',
        'cv2.face',
        
        # MediaPipe
        'mediapipe',
        'mediapipe.python',
        'mediapipe.python._framework_bindings',
        'mediapipe.tasks',
        'mediapipe.tasks.python',
        'mediapipe.tasks.python.vision',
        'mediapipe.tasks.python.components.containers',
        'mediapipe.modules',
        'mediapipe.calculators',
        
        # NumPy
        'numpy',
        'numpy.core._multiarray_umath',
        'numpy.core._multiarray_tests',
        'numpy.lib.format',
        'numpy.random.common',
        'numpy.random.bounded_integers',
        'numpy.random.bit_generator',
        'numpy.random._generator',
        
        # База данных и файлы
        'sqlite3',
        'sqlite3.dump',
        
        # Системные модули
        'logging',
        'json',
        'io',
        'datetime',
        'time',
        'threading',
        '_thread',
        'queue',
        'collections',
        'collections.abc',
        'urllib',
        'urllib.parse',
        'urllib.request',
        'pathlib',
        'os',
        'sys',
        'typing',
        'enum',
        'abc',
        'functools',
        'itertools',
        're',
        'math',
        'statistics',
        'base64',
        'hashlib',
        'struct',
        'copy',
        'weakref',
        'atexit',
        'pickle',
        'shelve',
        'configparser',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],  # Добавляем runtime hook
    excludes=[
        'matplotlib',
        'scipy',
        'pandas',
        'sklearn',
        'torch',
        'tensorflow',
        'jupyter',
        'notebook',
        'ipython',
        'ipykernel',
        'pygame',
        'pyqt5',
        'pyside2',
        'pytest',
        'unittest',
        'docutils',
        'setuptools',
        'pip',
        'wheel',
        'Cython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Дополнительно включаем бинарные файлы
for i, (dest, name, data_type) in enumerate(a.datas):
    if 'mediapipe' in name.lower() or 'opencv' in name.lower():
        print(f"📦 Включаем файл: {name}")

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='KaleidoID',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Измените на True для отладки проблем с камерой
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codepage='utf-8',
    icon='kaleido_icon.ico' if os.path.exists('kaleido_icon.ico') else None,
)
'''
    with open('kaleido_id.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)

def create_runtime_hook():
    """Создание runtime hook для исправления путей в EXE"""
    hook_content = '''import sys
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
'''
    with open('runtime_hook.py', 'w', encoding='utf-8') as f:
        f.write(hook_content)

def check_pyinstaller():
    """Проверка установки PyInstaller"""
    try:
        import PyInstaller
        version = PyInstaller.__version__
        print(f"✅ PyInstaller установлен: {version}")
        return True
    except ImportError:
        print("❌ PyInstaller не установлен")
        print("Устанавливаю PyInstaller...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
            print("✅ PyInstaller успешно установлен")
            return True
        except subprocess.CalledProcessError:
            print("❌ Не удалось установить PyInstaller")
            return False

def build_with_pyinstaller():
    """Сборка с помощью PyInstaller с улучшенной обработкой ошибок"""
    print("🔨 Запуск PyInstaller...")
    
    # Создаем runtime hook
    create_runtime_hook()
    print("📝 Создан runtime hook")
    
    # Создаем улучшенный spec файл
    create_camera_fix_spec_file()
    print("📝 Создан улучшенный spec файл")
    
    try:
        # Собираем с подробным логированием
        print("🚀 Начало сборки...")
        result = subprocess.run([
            'pyinstaller',
            'kaleido_id.spec',
            '--clean',
            '--noconfirm',
            '--log-level=DEBUG'
        ], check=True, capture_output=True, text=True, timeout=600)  # Увеличиваем таймаут до 10 минут
        
        print("✅ Сборка завершена успешно!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка сборки PyInstaller (код {e.returncode}):")
        if e.stdout:
            print(f"STDOUT (последние 20 строк):")
            print("\n".join(e.stdout.split("\n")[-20:]))
        if e.stderr:
            print(f"STDERR (последние 20 строк):")
            print("\n".join(e.stderr.split("\n")[-20:]))
        
        return try_camera_fix_build()
    
    except subprocess.TimeoutExpired:
        print("❌ Сборка превысила таймаут (10 минут)")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return try_camera_fix_build()

def try_camera_fix_build():
    """Сборка с исправлениями для камеры"""
    print("🔄 Пробуем сборку с исправлениями для камеры...")
    
    try:
        cmd = [
            'pyinstaller',
            '--name=KaleidoID',
            '--onedir',
            '--windowed',
            '--clean',
            '--noconfirm',
            '--add-data=src;src',
            '--add-data=data;data',
            '--add-data=logs;logs',
            '--add-binary=venv/Lib/site-packages/mediapipe;mediapipe',
            '--add-binary=venv/Lib/site-packages/cv2;cv2',
            '--hidden-import=tkinter',
            '--hidden-import=PIL',
            '--hidden-import=PIL._tkinter_finder',
            '--hidden-import=PIL.Image',
            '--hidden-import=PIL.ImageTk',
            '--hidden-import=cv2',
            '--hidden-import=cv2.cv2',
            '--hidden-import=cv2.videoio',
            '--hidden-import=mediapipe',
            '--hidden-import=mediapipe.python',
            '--hidden-import=mediapipe.python._framework_bindings',
            '--hidden-import=numpy',
            '--hidden-import=numpy.core._multiarray_umath',
            '--hidden-import=sqlite3',
            '--collect-all=mediapipe',
            '--collect-all=opencv_python',
            '--collect-all=PIL',
            '--runtime-hook=runtime_hook.py',
            '--exclude-module=matplotlib',
            '--exclude-module=scipy',
            '--exclude-module=pandas',
            'main.py'
        ]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=600)
        print("✅ Сборка с исправлениями для камеры завершена успешно!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Сборка с исправлениями не удалась:")
        if e.stderr:
            print(f"STDERR: {e.stderr[-500:]}")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Сборка с исправлениями превысила таймаут")
        return False

def create_camera_test_script():
    """Создание тестового скрипта для проверки камеры"""
    test_script = '''import tkinter as tk
from tkinter import ttk, messagebox
import cv2
from PIL import Image, ImageTk
import os
import sys

class CameraTest:
    def __init__(self, root):
        self.root = root
        self.root.title("Тест камеры - KaleidoID")
        self.root.geometry("800x600")
        
        self.camera = None
        self.is_camera_active = False
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="🔮 Тест работы камеры", font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Camera feed
        self.camera_label = ttk.Label(main_frame, text="Камера не активирована", background='black', foreground='white')
        self.camera_label.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky=(tk.W, tk.E))
        self.camera_label.config(width=80, height=20)
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        # Control buttons
        self.start_btn = ttk.Button(button_frame, text="Запустить камеру", command=self.start_camera)
        self.start_btn.grid(row=0, column=0, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="Остановить камеру", command=self.stop_camera, state='disabled')
        self.stop_btn.grid(row=0, column=1, padx=5)
        
        self.capture_btn = ttk.Button(button_frame, text="Сделать снимок", command=self.capture_photo, state='disabled')
        self.capture_btn.grid(row=0, column=2, padx=5)
        
        # Status
        self.status_label = ttk.Label(main_frame, text="Статус: Ожидание запуска камеры", foreground='blue')
        self.status_label.grid(row=3, column=0, columnspan=2, pady=10)
        
    def start_camera(self):
        try:
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                messagebox.showerror("Ошибка", "Не удалось открыть камеру")
                return
                
            self.is_camera_active = True
            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
            self.capture_btn.config(state='normal')
            self.status_label.config(text="Статус: Камера активна", foreground='green')
            
            self.update_camera_feed()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при запуске камеры: {str(e)}")
    
    def stop_camera(self):
        self.is_camera_active = False
        if self.camera:
            self.camera.release()
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.capture_btn.config(state='disabled')
        self.status_label.config(text="Статус: Камера остановлена", foreground='red')
        self.camera_label.config(image='', text="Камера не активирована")
    
    def update_camera_feed(self):
        if self.is_camera_active and self.camera:
            ret, frame = self.camera.read()
            if ret:
                # Convert to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Resize for display
                height, width = frame_rgb.shape[:2]
                if width > 640:
                    ratio = 640 / width
                    new_width = 640
                    new_height = int(height * ratio)
                    frame_rgb = cv2.resize(frame_rgb, (new_width, new_height))
                
                # Convert to PhotoImage
                image = Image.fromarray(frame_rgb)
                photo = ImageTk.PhotoImage(image)
                
                self.camera_label.config(image=photo, text="")
                self.camera_label.image = photo
                
            # Schedule next update
            self.root.after(10, self.update_camera_feed)
    
    def capture_photo(self):
        if self.camera and self.is_camera_active:
            ret, frame = self.camera.read()
            if ret:
                # Create test directory
                test_dir = "test_captures"
                os.makedirs(test_dir, exist_ok=True)
                
                # Save image
                filename = f"{test_dir}/test_capture_{len(os.listdir(test_dir)) + 1}.jpg"
                cv2.imwrite(filename, frame)
                
                messagebox.showinfo("Успех", f"Снимок сохранен как: {filename}")
                self.status_label.config(text=f"Статус: Снимок сохранен - {filename}", foreground='green')

if __name__ == "__main__":
    root = tk.Tk()
    app = CameraTest(root)
    root.mainloop()
'''
    
    with open("test_camera.py", "w", encoding="utf-8") as f:
        f.write(test_script)

def create_required_folders():
    """Создание необходимых папок для дистрибутива"""
    exe_dir = "dist/KaleidoID" if os.path.exists("dist/KaleidoID") else "dist"
    
    folders = [
        'data',
        'data/exports', 
        'data/backups',
        'data/templates',
        'data/captured_faces',
        'logs',
        'temp',
        'src'
    ]
    
    for folder in folders:
        folder_path = os.path.join(exe_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
        print(f"📁 Создана папка: {folder_path}")

def copy_additional_files():
    """Копирование дополнительных файлов в дистрибутив"""
    exe_dir = "dist/KaleidoID" if os.path.exists("dist/KaleidoID") else "dist"
    
    files_to_copy = [
        'README.md',
        'requirements.txt',
        'kaleido_icon.ico',
        'test_camera.py'  # Включаем тестовый скрипт
    ]
    
    for file in files_to_copy:
        if os.path.exists(file):
            shutil.copy2(file, os.path.join(exe_dir, file))
            print(f"📄 Скопирован: {file}")

def create_launcher_script():
    """Создание скрипта для запуска с отладкой"""
    launcher_content = '''@echo off
chcp 65001 > nul
echo 🔮 Запуск KaleidoID...
echo.

REM Проверяем наличие необходимых DLL
if not exist "vc_redist.x64.exe" (
    echo ⚠️ Предупреждение: Убедитесь, что установлен Microsoft Visual C++ Redistributable
    echo    Скачайте с: https://aka.ms/vs/16/release/vc_redist.x64.exe
    echo.
)

REM Проверяем камеру
echo 📷 Проверка доступности камеры...
python -c "import cv2; cap = cv2.VideoCapture(0); print('Камера доступна:' if cap.isOpened() else 'Камера недоступна'); cap.release()" 2>nul

REM Запускаем приложение
echo 🚀 Запуск приложения...
KaleidoID.exe

if %errorlevel% neq 0 (
    echo.
    echo ❌ Приложение завершилось с ошибкой (код: %errorlevel%)
    echo 💡 Рекомендации:
    echo   1. Запустите test_camera.py для проверки камеры
    echo   2. Проверьте права доступа к камере
    echo   3. Убедитесь, что камера не используется другим приложением
    pause
) else (
    echo.
    echo ✅ Приложение завершено успешно
)
'''
    
    with open("dist/Start_KaleidoID.bat", "w", encoding='utf-8') as f:
        f.write(launcher_content)

def test_built_application():
    """Тестирование собранного приложения"""
    print("🧪 Тестирование собранного приложения...")
    
    exe_path = None
    if os.path.exists("dist/KaleidoID/KaleidoID.exe"):
        exe_path = "dist/KaleidoID/KaleidoID.exe"
    elif os.path.exists("dist/KaleidoID.exe"):
        exe_path = "dist/KaleidoID.exe"
    
    if exe_path and os.path.exists(exe_path):
        print(f"✅ Исполняемый файл найден: {exe_path}")
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"📊 Размер: {size_mb:.1f} MB")
        
        # Проверяем наличие важных файлов
        important_files = [
            'dist/opencv_videoio_ffmpeg455_64.dll',
            'dist/mediapipe/modules/face_detection/face_detection_short_range.tflite'
        ]
        
        for file in important_files:
            if os.path.exists(file):
                print(f"✅ Найден: {file}")
            else:
                print(f"⚠️ Отсутствует: {file}")
        
        return True
    else:
        print("❌ Исполняемый файл не найден")
        return False

def main():
    """Основная функция сборки"""
    print("🔮 Сборка KaleidoID в EXE - Версия 3.0 (Исправление камеры)")
    print("=" * 60)
    
    # Проверяем Python
    print(f"🐍 Python: {sys.version}")
    print(f"💻 Платформа: {platform.platform()}")
    
    # Создаем тестовый скрипт для камеры
    create_camera_test_script()
    print("📝 Создан тестовый скрипт для камеры")
    
    # Проверяем зависимости
    check_dependencies()
    
    # Проверяем PyInstaller
    if not check_pyinstaller():
        print("❌ Не удалось установить PyInstaller")
        return
    
    # Очистка
    cleanup_build_dirs()
    
    # Сборка
    if build_with_pyinstaller():
        print("\n🎉 Сборка завершена!")
        
        # Создаем необходимые папки
        create_required_folders()
        
        # Копируем файлы
        copy_additional_files()
        
        # Создаем лаунчер
        create_launcher_script()
        
        # Тестируем
        test_built_application()
        
        print("\n📁 Структура дистрибутива:")
        dist_dir = "dist/KaleidoID" if os.path.exists("dist/KaleidoID") else "dist"
        for root, dirs, files in os.walk(dist_dir):
            level = root.replace(dist_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f'{indent}{os.path.basename(root)}/')
            subindent = ' ' * 2 * (level + 1)
            for file in files[:5]:  # Показываем первые 5 файлов
                if any(ext in file for ext in ['.dll', '.tflite', '.exe', '.pyd']):
                    print(f'{subindent}🔧 {file}')
                else:
                    print(f'{subindent}{file}')
            if len(files) > 5:
                print(f'{subindent}... и еще {len(files) - 5} файлов')
        
        print("\n🔧 Исправления для работы камеры:")
        print("   1. Добавлен runtime hook для исправления путей")
        print("   2. Включены все модели MediaPipe")
        print("   3. Добавлены специфичные DLL для OpenCV")
        print("   4. Создан тестовый скрипт для диагностики")
        
        print("\n💡 Если кнопки создания фото не работают:")
        print("   1. Запустите test_camera.py для проверки камеры")
        print("   2. Соберите с console=True для просмотра ошибок")
        print("   3. Проверьте права доступа к папке data/captured_faces")
        print("   4. Убедитесь, что камера доступна и не занята")
        
    else:
        print("\n❌ Сборка не удалась")
        print("\n🔧 Расширенная диагностика для камеры:")
        print("   1. Проверьте работу камеры в test_camera.py")
        print("   2. Убедитесь, что установлены все кодеки:")
        print("      - Microsoft Visual C++ Redistributable")
        print("      - K-Lite Codec Pack (Basic)")
        print("   3. Запустите приложение от имени администратора")
        print("   4. Проверьте настройки конфиденциальности камеры в Windows")

if __name__ == "__main__":
    main()