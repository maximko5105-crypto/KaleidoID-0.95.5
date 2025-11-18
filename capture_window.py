#!/usr/bin/env python3
"""
Окно захвата фотографий для KaleidoID
"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class CaptureWindow:
    """
    Окно для захвата фотографий с камеры при добавлении нового человека
    """
    
    def __init__(self, parent, database, recognizer, person_data):
        self.parent = parent
        self.database = database
        self.recognizer = recognizer
        self.person_data = person_data
        
        # Переменные для работы с камерой
        self.cap = None
        self.is_camera_active = False
        self.current_frame = None
        self.captured_photos = []
        
        # Создание окна
        self.window = tk.Toplevel(parent)
        self.window.title("📸 Захват фотографий для базы данных")
        self.window.geometry("1000x700")
        self.window.minsize(900, 600)
        self.window.transient(parent)
        self.window.grab_set()
        
        # Центрирование окна
        self.window.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.window.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.window.winfo_height()) // 2
        self.window.geometry(f"+{x}+{y}")
        
        # Настройка интерфейса
        self.setup_gui()
        
        # Запуск камеры
        self.start_camera()
        
        # Обработчик закрытия окна
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        logger.info(f"Capture window opened for person: {person_data.get('last_name', '')} {person_data.get('first_name', '')}")

    def setup_gui(self):
        """Настройка интерфейса окна захвата"""
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Заголовок
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(
            header_frame,
            text="📸 Захват фотографий для базы данных",
            font=("Arial", 16, "bold"),
            foreground="#2c3e50"
        )
        title_label.pack(side=tk.LEFT)
        
        # Информация о человеке
        person_name = f"{self.person_data.get('last_name', '')} {self.person_data.get('first_name', '')}"
        info_label = ttk.Label(
            header_frame,
            text=f"Для: {person_name}",
            font=("Arial", 12),
            foreground="#7f8c8d"
        )
        info_label.pack(side=tk.RIGHT)
        
        # Основной контент
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Левая часть - предпросмотр камеры
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Правая часть - управление и предпросмотр снимков
        right_frame = ttk.Frame(content_frame, width=300)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        right_frame.pack_propagate(False)
        
        # Область предпросмотра камеры
        camera_frame = ttk.LabelFrame(left_frame, text="Предпросмотр камеры", padding="10")
        camera_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.video_label = ttk.Label(
            camera_frame, 
            text="Инициализация камеры...",
            background="#1e1e1e",
            foreground="#cccccc",
            anchor="center",
            font=("Arial", 12)
        )
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        # Панель управления камерой
        control_frame = ttk.LabelFrame(left_frame, text="Управление съемкой", padding="10")
        control_frame.pack(fill=tk.X)
        
        control_buttons = ttk.Frame(control_frame)
        control_buttons.pack(fill=tk.X)
        
        self.capture_btn = ttk.Button(
            control_buttons,
            text="📷 Сделать снимок",
            command=self.capture_photo,
            state=tk.DISABLED
        )
        self.capture_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.retake_btn = ttk.Button(
            control_buttons,
            text="🔄 Повторить последний",
            command=self.retake_last_photo,
            state=tk.DISABLED
        )
        self.retake_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            control_buttons,
            text="💡 Подсказки",
            command=self.show_tips
        ).pack(side=tk.LEFT)
        
        # Статус съемки
        self.status_var = tk.StringVar(value="Готов к съемке")
        status_label = ttk.Label(control_frame, textvariable=self.status_var, foreground="#2c3e50")
        status_label.pack(anchor=tk.W, pady=(10, 0))
        
        # Область предпросмотра снимков
        photos_frame = ttk.LabelFrame(right_frame, text="Сделанные снимки", padding="10")
        photos_frame.pack(fill=tk.BOTH, expand=True)
        
        # Создаем canvas для предпросмотра снимков
        self.photos_canvas = tk.Canvas(photos_frame, bg="#f8f9fa")
        scrollbar = ttk.Scrollbar(photos_frame, orient=tk.VERTICAL, command=self.photos_canvas.yview)
        self.photos_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.photos_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Фрейм для миниатюр внутри canvas
        self.photos_frame = ttk.Frame(self.photos_canvas)
        self.canvas_window = self.photos_canvas.create_window((0, 0), window=self.photos_frame, anchor="nw")
        
        # Привязка событий для обновления прокрутки
        self.photos_frame.bind("<Configure>", self.on_frame_configure)
        self.photos_canvas.bind("<Configure>", self.on_canvas_configure)
        
        # Панель завершения
        finish_frame = ttk.LabelFrame(right_frame, text="Завершение", padding="10")
        finish_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(
            finish_frame, 
            text="Рекомендуется сделать 3-5 снимков\nс разных ракурсов для лучшего распознавания",
            font=("Arial", 9),
            foreground="#7f8c8d",
            justify=tk.CENTER
        ).pack(fill=tk.X, pady=5)
        
        finish_buttons = ttk.Frame(finish_frame)
        finish_buttons.pack(fill=tk.X, pady=(10, 0))
        
        self.finish_btn = ttk.Button(
            finish_buttons,
            text="✅ Завершить и сохранить",
            command=self.finish_and_save,
            state=tk.DISABLED
        )
        self.finish_btn.pack(fill=tk.X)
        
        ttk.Button(
            finish_buttons,
            text="❌ Отмена",
            command=self.on_closing
        ).pack(fill=tk.X, pady=(5, 0))

    def on_frame_configure(self, event):
        """Обновление области прокрутки при изменении размера фрейма"""
        self.photos_canvas.configure(scrollregion=self.photos_canvas.bbox("all"))

    def on_canvas_configure(self, event):
        """Обновление размера внутреннего фрейма при изменении canvas"""
        self.photos_canvas.itemconfig(self.canvas_window, width=event.width)

    def start_camera(self):
        """Запуск камеры"""
        try:
            camera_id = int(self.database.get_setting('camera_id', 0))
            self.cap = cv2.VideoCapture(camera_id)
            
            if not self.cap.isOpened():
                messagebox.showerror("Ошибка", "Не удалось подключиться к камере")
                self.window.destroy()
                return

            self.is_camera_active = True
            self.capture_btn.config(state=tk.NORMAL)
            self.status_var.set("Камера активна - готов к съемке")
            
            self.update_camera()

        except Exception as e:
            logger.error(f"Ошибка при запуске камеры: {e}")
            messagebox.showerror("Ошибка", f"Ошибка при запуске камеры: {e}")
            self.window.destroy()

    def stop_camera(self):
        """Остановка камеры"""
        self.is_camera_active = False
        if self.cap:
            self.cap.release()
            self.cap = None

    def update_camera(self):
        """Обновление видеопотока"""
        if self.is_camera_active and self.cap:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                # Сохраняем текущий кадр только если он валидный
                if hasattr(frame, 'size') and frame.size > 0:
                    self.current_frame = frame.copy()
                
                # Обнаружение лиц в реальном времени
                try:
                    faces = self.recognizer.detect_faces(frame)
                    
                    # Рисуем bounding box вокруг лиц
                    for face in faces:
                        if hasattr(face, 'bbox'):
                            x, y, w, h = face.bbox
                            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                            
                            # Добавляем текст с уверенностью
                            confidence = getattr(face, 'confidence', 0)
                            cv2.putText(frame, f"Face: {confidence:.2f}", (x, y-10), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                except Exception as e:
                    logger.warning(f"Ошибка обнаружения лиц: {e}")
                
                # Конвертируем для Tkinter
                try:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    img = img.resize((640, 480))
                    imgtk = ImageTk.PhotoImage(image=img)

                    self.video_label.imgtk = imgtk
                    self.video_label.configure(image=imgtk)
                except Exception as e:
                    logger.warning(f"Ошибка конвертации кадра: {e}")

            if self.is_camera_active:
                self.window.after(15, self.update_camera)

    def capture_photo(self):
        """Захват фотографии"""
        # Проверяем наличие кадра
        if self.current_frame is None:
            messagebox.showwarning("Предупреждение", "Нет активного кадра для захвата")
            return
        
        try:
            # Проверяем что current_frame является валидным numpy array
            if not hasattr(self.current_frame, 'size') or self.current_frame.size == 0:
                messagebox.showwarning("Предупреждение", "Невалидный кадр для захвата")
                return
                
            # Конвертируем frame в PIL Image
            frame_rgb = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            
            # Добавляем фото в список захваченных
            photo_data = {
                'image': pil_image,
                'timestamp': datetime.now(),
                'faces_detected': len(self.recognizer.detect_faces(self.current_frame))
            }
            
            self.captured_photos.append(photo_data)
            
            # Обновляем интерфейс
            self.update_photos_preview()
            self.update_buttons_state()
            
            self.status_var.set(f"Снимок #{len(self.captured_photos)} сохранен")
            
            # Показываем уведомление
            if len(self.captured_photos) == 1:
                messagebox.showinfo("Успех", "Первый снимок сделан! Сделайте еще 2-4 снимка с разных ракурсов.")
            
        except Exception as e:
            logger.error(f"Ошибка захвата фото: {e}")
            messagebox.showerror("Ошибка", f"Не удалось сохранить снимок: {e}")

    def retake_last_photo(self):
        """Повтор последнего снимка"""
        if self.captured_photos:
            self.captured_photos.pop()
            self.update_photos_preview()
            self.update_buttons_state()
            self.status_var.set("Последний снимок удален")

    def update_photos_preview(self):
        """Обновление предпросмотра снимков"""
        # Очищаем предыдущие миниатюры
        for widget in self.photos_frame.winfo_children():
            widget.destroy()
        
        # Создаем новые миниатюры
        for i, photo_data in enumerate(self.captured_photos):
            photo_frame = ttk.Frame(self.photos_frame, relief="solid", borderwidth=1)
            photo_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # Создаем миниатюру
            thumbnail = photo_data['image'].copy()
            thumbnail.thumbnail((120, 90))
            photo_img = ImageTk.PhotoImage(thumbnail)
            
            # Метка с изображением
            img_label = ttk.Label(photo_frame, image=photo_img)
            img_label.image = photo_img  # Сохраняем ссылку
            img_label.pack(side=tk.LEFT, padx=5, pady=5)
            
            # Информация о снимке
            info_frame = ttk.Frame(photo_frame)
            info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
            
            ttk.Label(
                info_frame, 
                text=f"Снимок #{i+1}",
                font=("Arial", 9, "bold")
            ).pack(anchor=tk.W)
            
            ttk.Label(
                info_frame,
                text=f"Время: {photo_data['timestamp'].strftime('%H:%M:%S')}",
                font=("Arial", 8)
            ).pack(anchor=tk.W)
            
            ttk.Label(
                info_frame,
                text=f"Лиц: {photo_data['faces_detected']}",
                font=("Arial", 8)
            ).pack(anchor=tk.W)
            
            # Кнопка удаления конкретного снимка
            delete_btn = ttk.Button(
                photo_frame,
                text="❌",
                width=3,
                command=lambda idx=i: self.delete_photo(idx)
            )
            delete_btn.pack(side=tk.RIGHT, padx=5)
        
        # Обновляем прокрутку
        self.photos_frame.update_idletasks()
        self.photos_canvas.configure(scrollregion=self.photos_canvas.bbox("all"))

    def delete_photo(self, index):
        """Удаление конкретного снимка"""
        if 0 <= index < len(self.captured_photos):
            self.captured_photos.pop(index)
            self.update_photos_preview()
            self.update_buttons_state()
            self.status_var.set(f"Снимок #{index+1} удален")

    def update_buttons_state(self):
        """Обновление состояния кнопок"""
        has_photos = len(self.captured_photos) > 0
        
        self.retake_btn.config(state=tk.NORMAL if has_photos else tk.DISABLED)
        self.finish_btn.config(state=tk.NORMAL if has_photos else tk.DISABLED)
        
        # Обновляем текст кнопки завершения
        if has_photos:
            self.finish_btn.config(text=f"✅ Завершить ({len(self.captured_photos)} снимков)")

    def finish_and_save(self):
        """Завершение съемки и сохранение в базу данных"""
        if not self.captured_photos:
            messagebox.showwarning("Предупреждение", "Нет снимков для сохранения")
            return
        
        try:
            # Сначала добавляем человека в базу если его еще нет
            if 'id' not in self.person_data or not self.person_data['id']:
                person_id = self.database.add_person(self.person_data)
                if not person_id:
                    messagebox.showerror("Ошибка", "Не удалось добавить человека в базу")
                    return
                self.person_data['id'] = person_id
            
            # Сохраняем все снимки
            saved_count = 0
            trained_count = 0
            
            for i, photo_data in enumerate(self.captured_photos):
                # Первый снимок делаем основным
                is_primary = (i == 0)
                
                # Добавляем фото в базу
                photo_id = self.database.add_person_photo(
                    self.person_data['id'],
                    photo_data['image'],
                    image_format="JPEG",
                    original_filename=f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}.jpg",
                    is_primary=is_primary
                )
                
                if photo_id:
                    saved_count += 1
                    
                    # Обучаем модель на новом фото если включена авто-обучение
                    if self.database.get_setting('auto_save_embeddings', '1') == '1':
                        success = self.recognizer.train_from_pil(
                            photo_data['image'], 
                            self.person_data, 
                            photo_id
                        )
                        
                        if success:
                            # Сохраняем эмбеддинг в базу
                            embedding = self.recognizer.extract_embedding_from_pil(photo_data['image'])
                            if embedding is not None:
                                self.database.update_photo_embedding(photo_id, embedding)
                            trained_count += 1
            
            # Показываем результат
            if saved_count > 0:
                messagebox.showinfo(
                    "Успех", 
                    f"Сохранено снимков: {saved_count}\n"
                    f"Обучено на фото: {trained_count}\n\n"
                    f"Человек успешно добавлен в базу данных!"
                )
                
                # Закрываем окно
                self.stop_camera()
                self.window.destroy()
                
                # Вызываем callback если установлен
                if hasattr(self, 'on_capture_complete'):
                    self.on_capture_complete(self.person_data['id'])
                    
            else:
                messagebox.showerror("Ошибка", "Не удалось сохранить ни одного снимка")
                
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных: {e}")
            messagebox.showerror("Ошибка", f"Ошибка при сохранении данных: {e}")

    def show_tips(self):
        """Показать подсказки по съемке"""
        tips = """
📸 Советы для качественных снимков:

1. **Освещение**:
   • Используйте равномерное естественное освещение
   • Избегайте резких теней и засветов
   • Не снимайте против источника света

2. **Позирование**:
   • Лицо должно быть прямо перед камерой
   • Сделайте снимки с разных ракурсов
   • Убедитесь, что все лицо видно

3. **Выражение лица**:
   • Используйте нейтральное выражение
   • Можно сделать снимки с улыбкой
   • Избегайте экстремальных выражений

4. **Качество**:
   • Убедитесь, что лицо в фокусе
   • Избегайте размытых снимков
   • Рекомендуется 3-5 снимков для надежности

Оптимальное количество: 3-5 снимков с разными ракурсами.
"""
        messagebox.showinfo("💡 Советы по съемке", tips)

    def on_closing(self):
        """Обработчик закрытия окна"""
        self.stop_camera()
        self.window.destroy()

    def __del__(self):
        """Деструктор - гарантирует освобождение ресурсов камеры"""
        self.stop_camera()