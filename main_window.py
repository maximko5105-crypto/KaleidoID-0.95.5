#!/usr/bin/env python3
"""
Главное окно KaleidoID с улучшенным отображением распознавания
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from PIL import Image, ImageTk
import cv2
import logging
from datetime import datetime
import os
import numpy as np
import json

logger = logging.getLogger(__name__)

class KaleidoIDGUI:
    """
    Главный GUI класс KaleidoID с улучшенным отображением распознавания
    """
    
    def __init__(self, root, database, recognizer):
        self.root = root
        self.database = database
        self.recognizer = recognizer
        
        # Переменные для работы с камерой
        self.cap = None
        self.is_camera_active = False
        self.current_frame = None
        self.current_person_id = None
        self.selected_person_id = None
        
        # Переменные для отображения распознавания
        self.current_recognition = None
        self.recognition_history = []
        self.max_history_size = 10
        
        # Настройка интерфейса
        self.setup_styles()
        self.setup_gui()
        
        # Загрузка начальных данных
        self.update_stats()
        self.update_model_info()
        
        logger.info("KaleidoID GUI инициализирован успешно")

    def setup_styles(self):
        """Настройка стилей интерфейса"""
        try:
            style = ttk.Style()
            style.theme_use('clam')
            
            # Кастомные стили
            style.configure('Kaleido.TFrame', background='#f5f6fa')
            style.configure('Kaleido.TLabel', background='#f5f6fa', font=('Arial', 10))
            style.configure('Kaleido.TButton', font=('Arial', 10))
            style.configure('Title.TLabel', font=('Arial', 16, 'bold'), foreground='#2c3e50')
            style.configure('Subtitle.TLabel', font=('Arial', 12, 'bold'), foreground='#34495e')
        except Exception as e:
            logger.warning(f"Не удалось настроить стили: {e}")

    def safe_float_format(self, value, format_str="{:.2f}"):
        """Безопасное форматирование чисел с обработкой ошибок"""
        if value is None:
            return format_str.format(0.0)
        try:
            return format_str.format(float(value))
        except (TypeError, ValueError):
            return format_str.format(0.0)

    def setup_gui(self):
        """Настройка основного интерфейса"""
        try:
            self.root.title("🔮 KaleidoID - Advanced Face Recognition System")
            self.root.geometry("1400x900")
            self.root.minsize(1200, 800)
            
            # Главный контейнер
            main_container = ttk.Frame(self.root, style='Kaleido.TFrame')
            main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Заголовок
            self.setup_header(main_container)
            
            # Вкладки
            self.setup_notebook(main_container)
            
            # Статус бар
            self.setup_status_bar()
            
        except Exception as e:
            logger.error(f"Ошибка настройки GUI: {e}")
            raise

    def setup_header(self, parent):
        """Настройка заголовка приложения"""
        header_frame = ttk.Frame(parent, style='Kaleido.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Логотип и название
        logo_frame = ttk.Frame(header_frame, style='Kaleido.TFrame')
        logo_frame.pack(side=tk.LEFT)
        
        title_label = ttk.Label(
            logo_frame, 
            text="🔮 KaleidoID",
            style='Title.TLabel'
        )
        title_label.pack(side=tk.LEFT)
        
        subtitle_label = ttk.Label(
            logo_frame,
            text="Advanced Face Recognition System",
            style='Subtitle.TLabel'
        )
        subtitle_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Кнопки быстрого доступа
        quick_actions = ttk.Frame(header_frame, style='Kaleido.TFrame')
        quick_actions.pack(side=tk.RIGHT)
        
        ttk.Button(
            quick_actions,
            text="🔄 Обновить",
            command=self.refresh_all
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            quick_actions,
            text="⚙️ Настройки",
            command=self.show_settings
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            quick_actions,
            text="📊 Статистика",
            command=self.show_system_stats
        ).pack(side=tk.LEFT)

    def setup_notebook(self, parent):
        """Настройка системы вкладок"""
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Создаем вкладки
        self.camera_tab = ttk.Frame(self.notebook)
        self.database_tab = ttk.Frame(self.notebook)
        self.management_tab = ttk.Frame(self.notebook)
        self.photos_tab = ttk.Frame(self.notebook)
        self.training_tab = ttk.Frame(self.notebook)
        self.analytics_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.camera_tab, text="🎥 Распознавание")
        self.notebook.add(self.database_tab, text="📊 База данных")
        self.notebook.add(self.management_tab, text="👤 Управление")
        self.notebook.add(self.photos_tab, text="🖼️ Фотографии")
        self.notebook.add(self.training_tab, text="🎓 Обучение")
        self.notebook.add(self.analytics_tab, text="📈 Аналитика")
        
        # Настраиваем содержимое вкладок
        self.setup_camera_tab()
        self.setup_database_tab()
        self.setup_management_tab()
        self.setup_photos_tab()
        self.setup_training_tab()
        self.setup_analytics_tab()

    def setup_camera_tab(self):
        """Настройка вкладки камеры и распознавания"""
        main_frame = ttk.Frame(self.camera_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        right_frame = ttk.Frame(main_frame, width=400)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        right_frame.pack_propagate(False)
        
        # Область видео
        video_frame = ttk.LabelFrame(left_frame, text="Видеопоток", padding="10")
        video_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.video_label = ttk.Label(
            video_frame, 
            text="Камера неактивна\n\nНажмите 'Запустить камеру'",
            background="#1e1e1e",
            foreground="#cccccc",
            anchor="center",
            font=("Arial", 12)
        )
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        # Панель управления камерой
        control_frame = ttk.LabelFrame(left_frame, text="Управление камерой", padding="10")
        control_frame.pack(fill=tk.X)
        
        control_buttons = ttk.Frame(control_frame)
        control_buttons.pack(fill=tk.X)
        
        self.start_btn = ttk.Button(
            control_buttons,
            text="▶ Запустить камеру",
            command=self.start_camera
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = ttk.Button(
            control_buttons,
            text="⏹ Остановить",
            command=self.stop_camera,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.capture_btn = ttk.Button(
            control_buttons,
            text="📷 Снимок для базы",
            command=self.capture_for_database,
            state=tk.DISABLED
        )
        self.capture_btn.pack(side=tk.LEFT)
        
        # Выбор человека для снимка
        person_select_frame = ttk.Frame(control_frame)
        person_select_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(person_select_frame, text="Добавить снимок для:").pack(side=tk.LEFT)
        
        self.camera_person_var = tk.StringVar()
        self.camera_person_combo = ttk.Combobox(
            person_select_frame, 
            textvariable=self.camera_person_var,
            state="readonly",
            width=30
        )
        self.camera_person_combo.pack(side=tk.LEFT, padx=(10, 0))
        self.camera_person_combo.bind('<<ComboboxSelected>>', self.on_camera_person_selected)
        
        # Настройки отображения
        display_frame = ttk.Frame(control_frame)
        display_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.show_landmarks_var = tk.BooleanVar(value=True)
        landmarks_check = ttk.Checkbutton(
            display_frame,
            text="🔍 Показывать landmarks лица",
            variable=self.show_landmarks_var,
            command=self.toggle_landmarks
        )
        landmarks_check.pack(side=tk.LEFT)
        
        self.show_connections_var = tk.BooleanVar(value=True)
        connections_check = ttk.Checkbutton(
            display_frame,
            text="📐 Показывать контуры лица",
            variable=self.show_connections_var,
            command=self.toggle_face_connections
        )
        connections_check.pack(side=tk.LEFT, padx=(10, 0))
        
        # Статистика в реальном времени
        stats_frame = ttk.LabelFrame(right_frame, text="📈 Статистика системы", padding="10")
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stats_text = tk.Text(
            stats_frame,
            height=8,
            bg="#f8f9fa",
            font=("Arial", 9),
            relief=tk.FLAT,
            wrap=tk.WORD
        )
        self.stats_text.pack(fill=tk.X)
        
        # Блок текущего распознавания
        recognition_frame = ttk.LabelFrame(right_frame, text="👁️ Текущее распознавание", padding="10")
        recognition_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.recognition_text = tk.Text(
            recognition_frame,
            height=6,
            bg="#f8f9fa",
            font=("Arial", 9),
            relief=tk.FLAT,
            wrap=tk.WORD
        )
        self.recognition_text.pack(fill=tk.X)
        
        # Настройки распознавания
        settings_frame = ttk.LabelFrame(right_frame, text="⚙️ Настройки распознавания", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(settings_frame, text="Порог распознавания:").pack(anchor=tk.W)
        
        self.threshold_var = tk.DoubleVar(value=0.75)
        threshold_scale = ttk.Scale(
            settings_frame,
            from_=0.1,
            to=1.0,
            variable=self.threshold_var,
            orient=tk.HORIZONTAL,
            command=self.update_threshold
        )
        threshold_scale.pack(fill=tk.X, pady=5)
        
        self.threshold_label = ttk.Label(settings_frame, text="0.75")
        self.threshold_label.pack(anchor=tk.W)
        
        # Журнал событий
        log_frame = ttk.LabelFrame(right_frame, text="📝 Журнал событий", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(
            log_frame,
            bg="#1e1e1e",
            fg="#cccccc",
            font=("Courier", 9),
            wrap=tk.WORD
        )
        
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Обновляем список людей для комбобокса
        self.update_camera_person_list()
        
        # Загружаем настройки
        self.load_camera_settings()

    def setup_database_tab(self):
        """Настройка вкладки базы данных"""
        main_frame = ttk.Frame(self.database_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Панель поиска и действий
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="Поиск:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(0, 10))
        search_entry.bind('<KeyRelease>', self.on_search)
        
        ttk.Button(search_frame, text="🔍 Поиск", command=self.search_database).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(search_frame, text="🔄 Обновить", command=self.refresh_database).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(search_frame, text="📤 Экспорт", command=self.export_selected_person).pack(side=tk.LEFT)
        
        # Таблица базы данных
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("ID", "Фамилия", "Имя", "Телефон", "Email", "Должность", "Отдел", "Фото")
        self.database_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        
        column_widths = [50, 120, 120, 120, 150, 150, 120, 60]
        for col, width in zip(columns, column_widths):
            self.database_tree.heading(col, text=col)
            self.database_tree.column(col, width=width, anchor=tk.CENTER)
        
        v_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.database_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.database_tree.xview)
        self.database_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.database_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Контекстное меню для таблицы
        self.setup_table_context_menu()
        
        # Загрузка данных
        self.refresh_database()

    def setup_management_tab(self):
        """Настройка вкладки управления людьми"""
        main_frame = ttk.Frame(self.management_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        right_frame = ttk.Frame(main_frame, width=300)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        right_frame.pack_propagate(False)
        
        # Форма редактирования
        self.setup_edit_form(left_frame)
        
        # Область предпросмотра
        self.setup_preview_area(right_frame)

    def setup_edit_form(self, parent):
        """Настройка формы редактирования данных человека"""
        form_frame = ttk.LabelFrame(parent, text="📝 Данные человека", padding="10")
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Поля формы
        fields = [
            ("Фамилия*:", "last_name"),
            ("Имя*:", "first_name"), 
            ("Отчество:", "middle_name"),
            ("Возраст:", "age"),
            ("Телефон:", "phone"),
            ("Email:", "email"),
            ("Должность:", "position"),
            ("Отдел:", "department"),
            ("Адрес:", "address")
        ]
        
        self.form_vars = {}
        for i, (label, field) in enumerate(fields):
            ttk.Label(form_frame, text=label).grid(row=i, column=0, sticky=tk.W, padx=10, pady=5)
            var = tk.StringVar()
            entry = ttk.Entry(form_frame, textvariable=var, font=("Arial", 10))
            entry.grid(row=i, column=1, sticky=tk.EW, padx=10, pady=5)
            self.form_vars[field] = var
        
        # Поле для заметок
        ttk.Label(form_frame, text="Дополнительные сведения:").grid(
            row=len(fields), column=0, sticky=tk.NW, padx=10, pady=5
        )
        self.notes_text = tk.Text(form_frame, height=6, width=40, font=("Arial", 10))
        self.notes_text.grid(row=len(fields), column=1, sticky=tk.EW, padx=10, pady=5)
        
        # Кнопки управления
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=20)
        
        ttk.Button(
            button_frame, 
            text="💾 Сохранить", 
            command=self.save_person
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            button_frame, 
            text="🆕 Новый", 
            command=self.new_person
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            button_frame, 
            text="📸 Снять фото с камеры", 
            command=self.open_capture_window
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            button_frame, 
            text="🎓 Обучить на всех фото", 
            command=self.batch_train_person
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            button_frame, 
            text="📤 Экспорт данных", 
            command=self.export_current_person
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            button_frame, 
            text="❌ Удалить", 
            command=self.delete_current_person
        ).pack(side=tk.LEFT)
        
        form_frame.grid_columnconfigure(1, weight=1)

    def setup_preview_area(self, parent):
        """Настройка области предпросмотра"""
        preview_frame = ttk.LabelFrame(parent, text="👤 Предпросмотр", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        self.preview_label = ttk.Label(
            preview_frame, 
            text="Выберите человека для просмотра",
            background="#f8f9fa",
            anchor="center",
            font=("Arial", 10)
        )
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        
        # Информация о выбранном человеке
        info_frame = ttk.Frame(preview_frame)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.person_info_text = tk.Text(
            info_frame,
            height=8,
            bg="#f8f9fa",
            font=("Arial", 9),
            relief=tk.FLAT,
            wrap=tk.WORD
        )
        self.person_info_text.pack(fill=tk.BOTH, expand=True)

    def setup_photos_tab(self):
        """Настройка вкладки управления фотографиями"""
        main_frame = ttk.Frame(self.photos_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Левая часть - список людей
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Правая часть - управление фотографиями
        right_frame = ttk.Frame(main_frame, width=500)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        right_frame.pack_propagate(False)
        
        # Список людей
        people_frame = ttk.LabelFrame(left_frame, text="👥 Список людей", padding="10")
        people_frame.pack(fill=tk.BOTH, expand=True)
        
        # Поиск в списке людей
        people_search_frame = ttk.Frame(people_frame)
        people_search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(people_search_frame, text="Поиск:").pack(side=tk.LEFT)
        self.people_search_var = tk.StringVar()
        people_search_entry = ttk.Entry(people_search_frame, textvariable=self.people_search_var)
        people_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        people_search_entry.bind('<KeyRelease>', self.on_people_search)
        
        self.people_listbox = tk.Listbox(people_frame, font=("Arial", 10))
        self.people_listbox.pack(fill=tk.BOTH, expand=True)
        self.people_listbox.bind('<<ListboxSelect>>', self.on_person_selected)
        
        # Область фотографий
        photos_frame = ttk.LabelFrame(right_frame, text="🖼️ Фотографии человека", padding="10")
        photos_frame.pack(fill=tk.BOTH, expand=True)
        
        # Панель управления фотографиями
        photo_controls = ttk.Frame(photos_frame)
        photo_controls.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            photo_controls,
            text="📁 Добавить фото",
            command=self.add_photo
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            photo_controls,
            text="🎓 Обучить на фото",
            command=self.train_selected_photo
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            photo_controls,
            text="🔄 Обновить список",
            command=self.refresh_photos_list
        ).pack(side=tk.LEFT)
        
        # Список фотографий
        photos_list_frame = ttk.Frame(photos_frame)
        photos_list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.photos_tree = ttk.Treeview(photos_list_frame, columns=("ID", "Файл", "Основная", "Эмбеддинг"), show="headings", height=10)
        self.photos_tree.heading("ID", text="ID")
        self.photos_tree.heading("Файл", text="Файл")
        self.photos_tree.heading("Основная", text="Основная")
        self.photos_tree.heading("Эмбеддинг", text="Эмбеддинг")
        
        self.photos_tree.column("ID", width=50)
        self.photos_tree.column("Файл", width=200)
        self.photos_tree.column("Основная", width=80)
        self.photos_tree.column("Эмбеддинг", width=80)
        
        photos_scrollbar = ttk.Scrollbar(photos_list_frame, orient=tk.VERTICAL, command=self.photos_tree.yview)
        self.photos_tree.configure(yscrollcommand=photos_scrollbar.set)
        
        self.photos_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        photos_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Контекстное меню для фотографий
        self.setup_photos_context_menu()
        
        # Предпросмотр фотографии
        preview_frame = ttk.LabelFrame(right_frame, text="👁️ Предпросмотр фото", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.photo_preview_label = ttk.Label(
            preview_frame, 
            text="Выберите фото для просмотра",
            background="#f8f9fa",
            anchor="center"
        )
        self.photo_preview_label.pack(fill=tk.BOTH, expand=True)
        
        # Загрузка начальных данных
        self.refresh_people_list()

    def setup_training_tab(self):
        """Настройка вкладки обучения модели"""
        main_frame = ttk.Frame(self.training_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        right_frame = ttk.Frame(main_frame, width=300)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        right_frame.pack_propagate(False)
        
        # Панель обучения
        training_frame = ttk.LabelFrame(left_frame, text="🎓 Управление обучением", padding="10")
        training_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(training_frame, text="Действия с моделью:").pack(anchor=tk.W, pady=5)
        
        ttk.Button(
            training_frame, 
            text="🔄 Перезагрузить все эмбеддинги", 
            command=self.reload_embeddings
        ).pack(fill=tk.X, pady=2)
        
        ttk.Button(
            training_frame, 
            text="📊 Статистика модели", 
            command=self.show_model_stats
        ).pack(fill=tk.X, pady=2)
        
        ttk.Button(
            training_frame, 
            text="🎯 Обучить всех людей", 
            command=self.batch_train_all
        ).pack(fill=tk.X, pady=2)
        
        ttk.Button(
            training_frame, 
            text="🧹 Очистка старых сессий", 
            command=self.cleanup_old_sessions
        ).pack(fill=tk.X, pady=2)
        
        # Расширенное обучение
        advanced_frame = ttk.LabelFrame(training_frame, text="🔧 Расширенное обучение", padding="10")
        advanced_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            advanced_frame, 
            text="📁 Обучить из папки", 
            command=self.batch_train_from_folder
        ).pack(fill=tk.X, pady=2)
        
        ttk.Button(
            advanced_frame, 
            text="💾 Экспорт эмбеддингов", 
            command=self.export_embeddings
        ).pack(fill=tk.X, pady=2)
        
        ttk.Button(
            advanced_frame, 
            text="📥 Импорт эмбеддингов", 
            command=self.import_embeddings
        ).pack(fill=tk.X, pady=2)
        
        # Резервное копирование
        backup_frame = ttk.LabelFrame(training_frame, text="💾 Резервное копирование", padding="10")
        backup_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            backup_frame, 
            text="📦 Создать бэкап БД", 
            command=self.backup_database
        ).pack(fill=tk.X, pady=2)
        
        # Информация о модели
        info_frame = ttk.LabelFrame(right_frame, text="ℹ️ Информация о модели", padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True)
        
        self.model_info_text = tk.Text(
            info_frame,
            bg="#f8f9fa",
            font=("Arial", 9),
            relief=tk.FLAT,
            height=15,
            wrap=tk.WORD
        )
        self.model_info_text.pack(fill=tk.BOTH, expand=True)

    def setup_analytics_tab(self):
        """Настройка вкладки аналитики"""
        main_frame = ttk.Frame(self.analytics_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Статистика использования
        stats_frame = ttk.LabelFrame(main_frame, text="📊 Статистика использования", padding="10")
        stats_frame.pack(fill=tk.BOTH, expand=True)
        
        self.analytics_text = tk.Text(
            stats_frame,
            bg="#f8f9fa",
            font=("Arial", 10),
            relief=tk.FLAT,
            wrap=tk.WORD
        )
        
        scrollbar = ttk.Scrollbar(stats_frame, command=self.analytics_text.yview)
        self.analytics_text.configure(yscrollcommand=scrollbar.set)
        
        self.analytics_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Обновляем аналитику
        self.update_analytics()

    def setup_status_bar(self):
        """Настройка строки состояния с улучшенной информацией"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_var = tk.StringVar(value="🔮 KaleidoID готов к работе")
        status_bar = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Индикатор состояния модели
        self.model_status_var = tk.StringVar(value="Модель: Загрузка...")
        model_status = ttk.Label(status_frame, textvariable=self.model_status_var, relief=tk.SUNKEN, anchor=tk.E)
        model_status.pack(side=tk.RIGHT)
        
        # Индикатор текущего распознавания
        self.recognition_status_var = tk.StringVar(value="Распознавание: ---")
        recognition_status = ttk.Label(status_frame, textvariable=self.recognition_status_var, relief=tk.SUNKEN, anchor=tk.CENTER)
        recognition_status.pack(side=tk.RIGHT, fill=tk.X, padx=5)

    def setup_table_context_menu(self):
        """Настройка контекстного меню для таблицы"""
        self.context_menu = tk.Menu(self.database_tree, tearoff=0)
        self.context_menu.add_command(label="📋 Редактировать", command=self.edit_selected_person)
        self.context_menu.add_command(label="👁️ Просмотреть", command=self.view_selected_person)
        self.context_menu.add_command(label="🖼️ Управление фото", command=self.manage_person_photos)
        self.context_menu.add_command(label="🎓 Обучить на всех фото", command=self.batch_train_selected_person)
        self.context_menu.add_command(label="📤 Экспорт данных", command=self.export_selected_person)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="❌ Удалить", command=self.delete_selected_person)
        
        self.database_tree.bind("<Button-3>", self.show_context_menu)

    def setup_photos_context_menu(self):
        """Настройка контекстного меню для фотографий"""
        self.photos_context_menu = tk.Menu(self.photos_tree, tearoff=0)
        self.photos_context_menu.add_command(label="Сделать основной", command=self.set_primary_photo)
        self.photos_context_menu.add_command(label="Обучить на фото", command=self.train_selected_photo)
        self.photos_context_menu.add_command(label="Удалить фото", command=self.delete_selected_photo)
        self.photos_tree.bind("<Button-3>", self.show_photos_context_menu)

    # === ОСНОВНЫЕ МЕТОДЫ РАБОТЫ С КАМЕРОЙ ===

    def start_camera(self):
        """Запуск камеры для распознавания"""
        try:
            camera_id = int(self.database.get_setting('camera_id', 0))
            self.cap = cv2.VideoCapture(camera_id)
            
            if not self.cap.isOpened():
                messagebox.showerror("Ошибка", "Не удалось подключиться к камере")
                return

            self.is_camera_active = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.capture_btn.config(state=tk.NORMAL)
            self.status_var.set("Камера активна - распознавание запущено")
            
            self.log("Камера запущена")
            self.update_camera()

        except Exception as e:
            logger.error(f"Ошибка при запуске камеры: {e}")
            messagebox.showerror("Ошибка", f"Ошибка при запуске камеры: {e}")

    def stop_camera(self):
        """Остановка камеры"""
        self.is_camera_active = False
        if self.cap:
            self.cap.release()
            self.cap = None

        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.capture_btn.config(state=tk.DISABLED)
        self.video_label.config(image='', text="Камера неактивна")
        self.status_var.set("Камера остановлена")
        
        self.log("Камера остановлена")

    def update_camera(self):
        """Обновление видеопотока с улучшенным распознаванием"""
        if self.is_camera_active and self.cap:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                # Сохраняем текущий кадр только если он валидный
                if hasattr(frame, 'size') and frame.size > 0:
                    self.current_frame = frame.copy()
                
                try:
                    # Распознавание лиц в кадре
                    recognition_results = self.recognizer.recognize_face_in_image(frame)
                    
                    # Сбрасываем текущее распознавание
                    self.current_recognition = None
                    
                    # Отрисовка результатов для каждого лица
                    for result in recognition_results:
                        person_name = None
                        person_info = None
                        
                        if result['person_id']:
                            person = self.database.get_person(result['person_id'])
                            if person:
                                person_name = f"{person.get('last_name', '')} {person.get('first_name', '')}".strip()
                                person_info = person
                                
                                # Сохраняем информацию о текущем распознавании
                                self.current_recognition = {
                                    'person': person,
                                    'confidence': result['recognition_confidence'],
                                    'timestamp': datetime.now()
                                }
                                
                                # Добавляем в историю
                                self.recognition_history.append(self.current_recognition)
                                if len(self.recognition_history) > self.max_history_size:
                                    self.recognition_history.pop(0)
                                
                                # Добавляем запись о распознавании
                                self.database.add_recognition_session(
                                    result['person_id'], 
                                    result['recognition_confidence']
                                )
                        
                        # УЛУЧШЕННАЯ ОТРИСОВКА: вместо стандартных надписей выводим имя человека
                        frame = self.draw_enhanced_detection(
                            frame, result, person_name, result['recognition_confidence'], person_info
                        )
                        
                        # Отрисовка landmarks если включено
                        if self.show_landmarks_var.get() and result.get('landmarks'):
                            frame = self.recognizer.draw_landmarks(frame, result['landmarks'])
                        
                        # Отрисовка контуров если включено
                        if self.show_connections_var.get() and result.get('landmarks'):
                            frame = self.recognizer.draw_face_connections(frame, result['landmarks'])
                    
                    # Обновляем информацию о текущем распознавании
                    self.update_recognition_display()
                    self.update_recognition_status()
                    
                    # Конвертируем для отображения в Tkinter
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    img = img.resize((640, 480))
                    imgtk = ImageTk.PhotoImage(image=img)

                    self.video_label.imgtk = imgtk
                    self.video_label.configure(image=imgtk)

                except Exception as e:
                    logger.error(f"Ошибка обработки кадра: {e}")
                    self.log(f"Ошибка обработки кадра: {e}")
            
            if self.is_camera_active:
                self.root.after(15, self.update_camera)

    def draw_enhanced_detection(self, frame, result, person_name, confidence, person_info=None):
        """
        Улучшенная отрисовка распознавания с отображением имени человека
        
        Args:
            frame: Кадр для отрисовки
            result: Результат распознавания
            person_name: Имя человека
            confidence: Уверенность распознавания
            person_info: Дополнительная информация о человеке
        """
        try:
            # Получаем координаты bounding box
            bbox = result.get('bbox', [])
            if not bbox or len(bbox) < 4:
                return frame
                
            x, y, w, h = bbox
            
            # Определяем цвет в зависимости от уверенности
            if confidence > 0.8:
                color = (0, 255, 0)  # Зеленый - высокая уверенность
            elif confidence > 0.6:
                color = (0, 255, 255)  # Желтый - средняя уверенность
            else:
                color = (0, 0, 255)  # Красный - низкая уверенность
            
            # Рисуем bounding box
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            # Подготавливаем текст для отображения
            if person_name and confidence > 0.5:  # Показываем имя только при достаточной уверенности
                display_text = person_name
                
                # Добавляем должность если есть
                if person_info and person_info.get('position'):
                    position = person_info.get('position')
                    if len(position) > 20:  # Обрезаем длинные должности
                        position = position[:20] + "..."
                    display_text += f" | {position}"
            else:
                display_text = "Неизвестное лицо"
            
            # Добавляем уверенность
            confidence_text = f"{confidence:.1%}"
            
            # Вычисляем размеры текста для фона
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 2
            
            # Получаем размеры основного текста
            (text_width, text_height), baseline = cv2.getTextSize(display_text, font, font_scale, thickness)
            
            # Рисуем фон для текста
            cv2.rectangle(frame, 
                         (x, y - text_height - 10), 
                         (x + text_width + 10, y), 
                         color, -1)
            
            # Рисуем основной текст (имя)
            cv2.putText(frame, display_text, 
                       (x + 5, y - 5), 
                       font, font_scale, (255, 255, 255), thickness)
            
            # Рисуем текст с уверенностью под bounding box
            if confidence > 0.5:  # Показываем уверенность только для распознанных лиц
                confidence_bg_y = y + h + 20
                (conf_width, conf_height), _ = cv2.getTextSize(confidence_text, font, font_scale - 0.1, thickness - 1)
                
                # Фон для уверенности
                cv2.rectangle(frame,
                            (x, confidence_bg_y - conf_height - 5),
                            (x + conf_width + 10, confidence_bg_y + 5),
                            color, -1)
                
                # Текст уверенности
                cv2.putText(frame, confidence_text,
                          (x + 5, confidence_bg_y),
                          font, font_scale - 0.1, (255, 255, 255), thickness - 1)
            
            return frame
            
        except Exception as e:
            logger.error(f"Ошибка в улучшенной отрисовке: {e}")
            return frame

    def update_recognition_display(self):
        """Обновление информации о текущем распознавании"""
        try:
            if self.current_recognition:
                person = self.current_recognition['person']
                confidence = self.current_recognition['confidence']
                timestamp = self.current_recognition['timestamp']
                
                # Формируем подробную информацию
                info_text = f"""🔍 РАСПОЗНАН ЧЕЛОВЕК:

👤 ФИО: {person.get('last_name', '')} {person.get('first_name', '')} {person.get('middle_name', '')}
🎯 Уверенность: {confidence:.2%}
⏰ Время: {timestamp.strftime('%H:%M:%S')}

📋 Информация:
• Возраст: {person.get('age', 'не указан')}
• Должность: {person.get('position', 'не указана')}
• Отдел: {person.get('department', 'не указан')}
• Телефон: {person.get('phone', 'не указан')}
• Email: {person.get('email', 'не указан')}

💡 Статус: {"✅ Высокая уверенность" if confidence > 0.8 else "⚠️ Средняя уверенность" if confidence > 0.6 else "❌ Низкая уверенность"}
"""
            else:
                info_text = "👁️ Лиц не распознано\n\nКамера активна. Наведите камеру на лицо для распознавания."
            
            self.recognition_text.delete(1.0, tk.END)
            self.recognition_text.insert(1.0, info_text)
            
        except Exception as e:
            logger.error(f"Ошибка обновления отображения распознавания: {e}")

    def update_recognition_status(self):
        """Обновление статуса распознавания в статусбаре"""
        if self.current_recognition:
            person = self.current_recognition['person']
            confidence = self.current_recognition['confidence']
            name = f"{person.get('last_name', '')} {person.get('first_name', '')}"
            status = f"Распознан: {name} ({confidence:.1%})"
        else:
            status = "Распознавание: ожидание..."
        
        self.recognition_status_var.set(status)

    def capture_for_database(self):
        """Сделать снимок для добавления в базу данных"""
        # Проверяем наличие кадра и выбранного человека
        if self.current_frame is None:
            messagebox.showwarning("Предупреждение", "Нет активного кадра для захвата")
            return
            
        if not self.current_person_id:
            messagebox.showwarning("Предупреждение", 
                "Сначала выберите человека из списка для добавления снимка")
            return
        
        try:
            # Проверяем что current_frame является валидным numpy array
            if not hasattr(self.current_frame, 'size') or self.current_frame.size == 0:
                messagebox.showwarning("Предупреждение", "Невалидный кадр для захвата")
                return
                
            # Конвертируем frame в PIL Image
            frame_rgb = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            
            # Добавляем фото в базу
            photo_id = self.database.add_person_photo(
                self.current_person_id, 
                pil_image,
                image_format="JPEG",
                original_filename=f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            )
            
            if photo_id:
                self.log(f"Добавлено фото для человека ID: {self.current_person_id}")
                messagebox.showinfo("Успех", "Фото успешно добавлено в базу данных")
                
                # Обучаем модель на новом фото если включена авто-обучение
                if self.database.get_setting('auto_save_embeddings', '1') == '1':
                    person = self.database.get_person(self.current_person_id)
                    if person:
                        success = self.recognizer.train_from_pil(pil_image, person, photo_id)
                        if success:
                            # Сохраняем эмбеддинг в базу
                            embedding = self.recognizer.extract_embedding_from_pil(pil_image)
                            if embedding is not None:
                                self.database.update_photo_embedding(photo_id, embedding)
                            self.log("Модель обучена на новом фото")
                            self.update_model_info()
            else:
                messagebox.showerror("Ошибка", "Не удалось добавить фото в базу")
                
        except Exception as e:
            logger.error(f"Ошибка сохранения снимка: {e}")
            messagebox.showerror("Ошибка", f"Не удалось сохранить снимок: {e}")
            self.log(f"Ошибка сохранения снимка: {e}")

    def toggle_landmarks(self):
        """Переключение отображения landmarks"""
        self.recognizer.toggle_landmarks(self.show_landmarks_var.get())
        self.log(f"Landmarks: {'включены' if self.show_landmarks_var.get() else 'отключены'}")

    def toggle_face_connections(self):
        """Переключение отображения контуров лица"""
        self.recognizer.toggle_face_connections(self.show_connections_var.get())
        self.log(f"Контуры лица: {'включены' if self.show_connections_var.get() else 'отключены'}")

    def open_capture_window(self):
        """Открытие окна для захвата фотографий с камеры"""
        # Проверяем, заполнены ли обязательные поля
        if not self.form_vars["last_name"].get() or not self.form_vars["first_name"].get():
            messagebox.showwarning("Предупреждение", "Заполните обязательные поля: Фамилия и Имя")
            return
        
        try:
            # Динамический импорт для избежания циклических зависимостей
            from src.gui.capture_window import CaptureWindow
            
            # Собираем данные человека
            person_data = {
                "last_name": self.form_vars["last_name"].get(),
                "first_name": self.form_vars["first_name"].get(),
                "middle_name": self.form_vars["middle_name"].get(),
                "age": self.form_vars["age"].get(),
                "phone": self.form_vars["phone"].get(),
                "email": self.form_vars["email"].get(),
                "position": self.form_vars["position"].get(),
                "department": self.form_vars["department"].get(),
                "address": self.form_vars["address"].get(),
                "notes": self.notes_text.get(1.0, tk.END).strip()
            }
            
            # Если человек уже существует, используем его ID
            if self.current_person_id:
                person_data['id'] = self.current_person_id
            
            # Открываем окно захвата
            capture_window = CaptureWindow(self.root, self.database, self.recognizer, person_data)
            
            # Настраиваем обработчик завершения
            def on_capture_complete(person_id):
                self.log(f"Захват фотографий завершен для человека ID: {person_id}")
                self.load_person_for_edit(person_id)
                self.refresh_database()
                self.update_stats()
                self.update_model_info()
            
            capture_window.on_capture_complete = on_capture_complete
            
        except ImportError as e:
            logger.error(f"Модуль захвата недоступен: {e}")
            messagebox.showerror("Ошибка", f"Модуль захвата недоступен: {e}")
        except Exception as e:
            logger.error(f"Ошибка при открытии окна захвата: {e}")
            messagebox.showerror("Ошибка", f"Ошибка при открытии окна захвата: {e}")

    # === МЕТОДЫ РАБОТЫ С БАЗОЙ ДАННЫХ ===

    def refresh_database(self):
        """Обновление таблицы базы данных"""
        try:
            # Очищаем таблицу
            for item in self.database_tree.get_children():
                self.database_tree.delete(item)
            
            # Загружаем данные
            people = self.database.get_all_people()
            for person in people:
                # Проверяем есть ли фото у человека
                has_photos = "✅" if self.database.get_person_photos(person['id']) else "❌"
                
                self.database_tree.insert("", tk.END, values=(
                    person.get("id", ""),
                    person.get("last_name", ""),
                    person.get("first_name", ""),
                    person.get("phone", ""),
                    person.get("email", ""),
                    person.get("position", ""),
                    person.get("department", ""),
                    has_photos
                ))
                
            self.log(f"База данных обновлена. Записей: {len(people)}")
            
        except Exception as e:
            logger.error(f"Ошибка обновления базы данных: {e}")
            self.log(f"Ошибка обновления базы данных: {e}")

    def search_database(self):
        """Поиск в базе данных"""
        search_term = self.search_var.get().strip()
        if not search_term:
            self.refresh_database()
            return
        
        try:
            # Очищаем таблицу
            for item in self.database_tree.get_children():
                self.database_tree.delete(item)
            
            # Выполняем поиск
            results = self.database.search_people(search_term)
            for person in results:
                has_photos = "✅" if self.database.get_person_photos(person['id']) else "❌"
                
                self.database_tree.insert("", tk.END, values=(
                    person.get("id", ""),
                    person.get("last_name", ""),
                    person.get("first_name", ""),
                    person.get("phone", ""),
                    person.get("email", ""),
                    person.get("position", ""),
                    person.get("department", ""),
                    has_photos
                ))
                
            self.log(f"Найдено записей: {len(results)} по запросу: '{search_term}'")
            
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            self.log(f"Ошибка поиска: {e}")

    def on_search(self, event):
        """Обработка поиска при вводе текста"""
        self.search_database()

    # === МЕТОДЫ РАБОТЫ С ЗАПИСЯМИ ЛЮДЕЙ ===

    def new_person(self):
        """Создание новой записи человека"""
        self.current_person_id = None
        for var in self.form_vars.values():
            var.set("")
        self.notes_text.delete(1.0, tk.END)
        self.preview_label.config(image="", text="Выберите человека для просмотра")
        self.person_info_text.delete(1.0, tk.END)
        self.log("Создание новой записи")

    def save_person(self):
        """Сохранение данных человека"""
        if not self.form_vars["last_name"].get() or not self.form_vars["first_name"].get():
            messagebox.showwarning("Предупреждение", "Заполните обязательные поля: Фамилия и Имя")
            return
        
        try:
            person_data = {
                "last_name": self.form_vars["last_name"].get(),
                "first_name": self.form_vars["first_name"].get(),
                "middle_name": self.form_vars["middle_name"].get(),
                "age": self.form_vars["age"].get(),
                "phone": self.form_vars["phone"].get(),
                "email": self.form_vars["email"].get(),
                "position": self.form_vars["position"].get(),
                "department": self.form_vars["department"].get(),
                "address": self.form_vars["address"].get(),
                "notes": self.notes_text.get(1.0, tk.END).strip()
            }
            
            # Преобразуем возраст в число
            if person_data['age']:
                try:
                    person_data['age'] = int(person_data['age'])
                except ValueError:
                    messagebox.showerror("Ошибка", "Возраст должен быть числом")
                    return
            
            success = False
            if self.current_person_id:
                # Обновление существующей записи
                success = self.database.update_person(self.current_person_id, person_data)
                action = "обновлена"
            else:
                # Создание новой записи
                person_id = self.database.add_person(person_data)
                success = person_id is not None
                if success:
                    self.current_person_id = person_id
                action = "добавлена"
            
            if success:
                messagebox.showinfo("Успех", f"Запись {action} успешно!")
                person_name = f"{person_data['last_name']} {person_data['first_name']}"
                self.log(f"Запись {action}: {person_name}")
                self.refresh_database()
                self.update_stats()
                self.update_camera_person_list()
                if not self.current_person_id:
                    self.new_person()
            else:
                messagebox.showerror("Ошибка", f"Не удалось {action} запись")
                
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
            messagebox.showerror("Ошибка", f"Ошибка сохранения: {e}")
            self.log(f"Ошибка сохранения: {e}")

    def load_person_for_edit(self, person_id):
        """Загрузка данных человека для редактирования"""
        try:
            person = self.database.get_person_with_photos(person_id)
            if person:
                self.current_person_id = person_id
                
                # Заполняем форму данными
                self.form_vars["last_name"].set(person.get("last_name", ""))
                self.form_vars["first_name"].set(person.get("first_name", ""))
                self.form_vars["middle_name"].set(person.get("middle_name", ""))
                
                age = person.get("age", "")
                self.form_vars["age"].set(str(age) if age else "")
                
                self.form_vars["phone"].set(person.get("phone", ""))
                self.form_vars["email"].set(person.get("email", ""))
                self.form_vars["position"].set(person.get("position", ""))
                self.form_vars["department"].set(person.get("department", ""))
                self.form_vars["address"].set(person.get("address", ""))
                
                self.notes_text.delete(1.0, tk.END)
                self.notes_text.insert(1.0, person.get("notes", ""))
                
                # Показываем основное фото
                primary_photo_id = self.database.get_primary_photo(person_id)
                if primary_photo_id:
                    self.show_photo_preview(primary_photo_id)
                else:
                    self.preview_label.config(image="", text="Основное фото не установлено")
                
                # Обновляем информацию о человеке
                self.update_person_info(person)
                
                person_name = f"{person.get('last_name', '')} {person.get('first_name', '')}"
                self.log(f"Загружена запись: {person_name}")
                
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            messagebox.showerror("Ошибка", f"Ошибка загрузки данных: {e}")
            self.log(f"Ошибка загрузки человека {person_id}: {e}")

    def update_person_info(self, person):
        """Обновление информации о человеке в интерфейсе"""
        try:
            stats = self.database.get_recognition_stats(person['id'])
            
            info_text = f"""Информация о человеке:

ФИО: {person.get('last_name', '')} {person.get('first_name', '')} {person.get('middle_name', '')}
Возраст: {person.get('age', '')}
Телефон: {person.get('phone', '')}
Email: {person.get('email', '')}
Должность: {person.get('position', '')}
Отдел: {person.get('department', '')}
Адрес: {person.get('address', '')}

Заметки:
{person.get('notes', '')}

Статистика:
• Фотографий: {len(person.get('photos', []))}
• Распознаваний: {stats.get('count', 0)}
• Средняя точность: {self.safe_float_format(stats.get('avg_confidence', 0), '{:.2%}')}
• Последний раз: {stats.get('last_seen', 'Никогда')}
"""
            self.person_info_text.delete(1.0, tk.END)
            self.person_info_text.insert(1.0, info_text)
            
        except Exception as e:
            logger.error(f"Ошибка обновления информации: {e}")
            self.log(f"Ошибка обновления информации: {e}")

    def show_photo_preview(self, photo_id):
        """Показать превью фотографии"""
        try:
            pil_image = self.database.get_photo_as_image(photo_id)
            if pil_image:
                # Масштабируем изображение для предпросмотра
                pil_image.thumbnail((250, 250))
                photo = ImageTk.PhotoImage(pil_image)
                self.preview_label.configure(image=photo, text="")
                self.preview_label.image = photo
        except Exception as e:
            logger.error(f"Ошибка загрузки изображения: {e}")
            self.preview_label.configure(image="", text="Ошибка загрузки изображения")
            self.log(f"Ошибка загрузки изображения: {e}")

    # === МЕТОДЫ РАБОТЫ С ФОТОГРАФИЯМИ ===

    def refresh_people_list(self):
        """Обновление списка людей"""
        try:
            self.people_listbox.delete(0, tk.END)
            people = self.database.get_all_people()
            for person in people:
                name = f"{person.get('last_name', '')} {person.get('first_name', '')} (ID: {person.get('id', '')})"
                self.people_listbox.insert(tk.END, name)
                
            self.log(f"Список людей обновлен. Записей: {len(people)}")
            
        except Exception as e:
            logger.error(f"Ошибка обновления списка людей: {e}")
            self.log(f"Ошибка обновления списка людей: {e}")

    def on_people_search(self, event):
        """Поиск в списке людей"""
        search_term = self.people_search_var.get().lower().strip()
        self.people_listbox.delete(0, tk.END)
        
        try:
            people = self.database.get_all_people()
            for person in people:
                name = f"{person.get('last_name', '')} {person.get('first_name', '')} (ID: {person.get('id', '')})"
                if search_term in name.lower():
                    self.people_listbox.insert(tk.END, name)
        except Exception as e:
            logger.error(f"Ошибка поиска людей: {e}")
            self.log(f"Ошибка поиска людей: {e}")

    def refresh_photos_list(self):
        """Обновление списка фотографий"""
        if not hasattr(self, 'selected_person_id') or not self.selected_person_id:
            return
        
        try:
            # Очищаем список
            for item in self.photos_tree.get_children():
                self.photos_tree.delete(item)
            
            # Загружаем фотографии
            photos = self.database.get_person_photos(self.selected_person_id)
            for photo in photos:
                filename = photo.get('original_filename', f"photo_{photo['id']}")
                is_primary = "✅" if photo.get('is_primary') else "❌"
                has_embedding = "✅" if photo.get('face_embedding') else "❌"
                
                self.photos_tree.insert("", tk.END, values=(
                    photo.get('id', ''),
                    filename,
                    is_primary,
                    has_embedding
                ))
                
            self.log(f"Загружено фотографий: {len(photos)}")
            
        except Exception as e:
            logger.error(f"Ошибка обновления списка фото: {e}")
            self.log(f"Ошибка обновления списка фото: {e}")

    def on_person_selected(self, event):
        """Обработка выбора человека в списке"""
        selection = self.people_listbox.curselection()
        if selection:
            index = selection[0]
            person_text = self.people_listbox.get(index)
            try:
                # Извлекаем ID из текста
                person_id = int(person_text.split('ID: ')[1].rstrip(')'))
                self.selected_person_id = person_id
                self.refresh_photos_list()
                
                # Загружаем данные человека
                person = self.database.get_person_with_photos(person_id)
                if person:
                    self.update_person_info(person)
            except (IndexError, ValueError) as e:
                logger.error(f"Ошибка извлечения ID: {e}")
                self.log(f"Ошибка извлечения ID: {e}")

    def add_photo(self):
        """Добавление фотографии из файла"""
        if not hasattr(self, 'selected_person_id') or not self.selected_person_id:
            messagebox.showwarning("Предупреждение", "Сначала выберите человека")
            return
        
        file_paths = filedialog.askopenfilenames(
            title="Выберите фотографии",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
        )
        
        if file_paths:
            added_count = 0
            for file_path in file_paths:
                try:
                    # Первое фото делаем основным
                    is_primary = (added_count == 0)
                    photo_id = self.database.add_person_photo_from_file(
                        self.selected_person_id, 
                        file_path, 
                        is_primary=is_primary
                    )
                    if photo_id:
                        added_count += 1
                        self.log(f"Добавлено фото: {os.path.basename(file_path)}")
                except Exception as e:
                    logger.error(f"Ошибка добавления фото {file_path}: {e}")
                    self.log(f"Ошибка добавления фото {file_path}: {e}")
            
            if added_count > 0:
                messagebox.showinfo("Успех", f"Добавлено {added_count} фотографий")
                self.refresh_photos_list()
                self.update_stats()
            else:
                messagebox.showerror("Ошибка", "Не удалось добавить фотографии")

    def train_selected_photo(self):
        """Обучение модели на выбранной фотографии"""
        selection = self.photos_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите фотографию для обучения")
            return
        
        item = selection[0]
        photo_id = self.photos_tree.item(item)["values"][0]
        
        try:
            person = self.database.get_person(self.selected_person_id)
            if person:
                pil_image = self.database.get_photo_as_image(photo_id)
                if pil_image:
                    success = self.recognizer.train_from_pil(pil_image, person, photo_id)
                    
                    if success:
                        # Сохраняем эмбеддинг в базу
                        embedding = self.recognizer.extract_embedding_from_pil(pil_image)
                        if embedding is not None:
                            self.database.update_photo_embedding(photo_id, embedding)
                        
                        messagebox.showinfo("Успех", "Модель обучена на выбранной фотографии")
                        self.log(f"Обучена модель на фото ID: {photo_id}")
                        self.refresh_photos_list()
                        self.update_model_info()
                    else:
                        messagebox.showerror("Ошибка", "Не удалось обучить модель на этой фотографии")
        except Exception as e:
            logger.error(f"Ошибка обучения: {e}")
            messagebox.showerror("Ошибка", f"Ошибка обучения: {e}")
            self.log(f"Ошибка обучения на фото: {e}")

    def set_primary_photo(self):
        """Установка выбранной фотографии как основной"""
        selection = self.photos_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        photo_id = self.photos_tree.item(item)["values"][0]
        
        try:
            if self.database.set_primary_photo(photo_id):
                messagebox.showinfo("Успех", "Фотография установлена как основная")
                self.refresh_photos_list()
            else:
                messagebox.showerror("Ошибка", "Не удалось установить фотографию как основную")
        except Exception as e:
            logger.error(f"Ошибка установки основной фото: {e}")
            messagebox.showerror("Ошибка", f"Ошибка установки основной фото: {e}")

    def delete_selected_photo(self):
        """Удаление выбранной фотографии"""
        selection = self.photos_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        photo_id = self.photos_tree.item(item)["values"][0]
        filename = self.photos_tree.item(item)["values"][1]
        
        if messagebox.askyesno("Подтверждение", f"Удалить фотографию {filename}?"):
            try:
                if self.database.delete_photo(photo_id):
                    # Удаляем эмбеддинг из модели
                    self.recognizer.remove_embedding_by_photo_id(photo_id)
                    
                    messagebox.showinfo("Успех", "Фотография удалена")
                    self.log(f"Удалена фотография ID: {photo_id}")
                    self.refresh_photos_list()
                    self.update_stats()
                    self.update_model_info()
                else:
                    messagebox.showerror("Ошибка", "Не удалось удалить фотографию")
            except Exception as e:
                logger.error(f"Ошибка удаления фото: {e}")
                messagebox.showerror("Ошибка", f"Ошибка удаления фото: {e}")

    def show_photos_context_menu(self, event):
        """Показать контекстное меню для фотографий"""
        item = self.photos_tree.identify_row(event.y)
        if item:
            self.photos_tree.selection_set(item)
            self.photos_context_menu.post(event.x_root, event.y_root)

    # === МЕТОДЫ ОБУЧЕНИЯ МОДЕЛИ ===

    def batch_train_person(self):
        """Пакетное обучение для текущего человека"""
        if not self.current_person_id:
            messagebox.showwarning("Предупреждение", "Сначала выберите человека")
            return
        
        try:
            person = self.database.get_person(self.current_person_id)
            if person:
                trained_count = self.recognizer.batch_train_person(
                    self.current_person_id,
                    f"{person.get('last_name', '')} {person.get('first_name', '')}",
                    self.database
                )
                
                if trained_count > 0:
                    messagebox.showinfo("Успех", f"Обучено на {trained_count} фотографиях")
                    self.log(f"Пакетное обучение для {person.get('last_name', '')}: {trained_count} фото")
                    self.update_model_info()
                else:
                    messagebox.showwarning("Предупреждение", "Нет фотографий для обучения или они уже обучены")
        except Exception as e:
            logger.error(f"Ошибка пакетного обучения: {e}")
            messagebox.showerror("Ошибка", f"Ошибка пакетного обучения: {e}")
            self.log(f"Ошибка пакетного обучения: {e}")

    def batch_train_all(self):
        """Пакетное обучение для всех людей в базе"""
        if messagebox.askyesno("Подтверждение", "Обучить модель на всех фотографиях всех людей?\n\nЭто может занять некоторое время."):
            try:
                total_trained = 0
                people = self.database.get_all_people()
                
                for person in people:
                    trained_count = self.recognizer.batch_train_person(
                        person['id'],
                        f"{person.get('last_name', '')} {person.get('first_name', '')}",
                        self.database
                    )
                    total_trained += trained_count
                
                messagebox.showinfo("Успех", f"Обучение завершено!\nОбучено на {total_trained} фотографиях")
                self.log(f"Пакетное обучение всех людей: {total_trained} фото")
                self.update_model_info()
                
            except Exception as e:
                logger.error(f"Ошибка обучения: {e}")
                messagebox.showerror("Ошибка", f"Ошибка обучения: {e}")
                self.log(f"Ошибка пакетного обучения всех: {e}")

    def batch_train_from_folder(self):
        """Групповое обучение из папки с изображениями"""
        folder_path = filedialog.askdirectory(title="Выберите папку с изображениями")
        if not folder_path:
            return
        
        last_name = simpledialog.askstring("Обучение", "Введите фамилию для всех изображений:")
        first_name = simpledialog.askstring("Обучение", "Введите имя для всех изображений:")
        
        if not last_name or not first_name:
            return
        
        try:
            # Создаем запись человека
            person_data = {
                'last_name': last_name,
                'first_name': first_name,
                'position': 'Автоматическое добавление',
                'department': 'Пакетное обучение'
            }
            
            person_id = self.database.add_person(person_data)
            if not person_id:
                messagebox.showerror("Ошибка", "Не удалось создать запись человека")
                return
            
            trained_count = 0
            error_count = 0
            
            for filename in os.listdir(folder_path):
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                    file_path = os.path.join(folder_path, filename)
                    
                    try:
                        # Добавляем фото
                        is_primary = (trained_count == 0)
                        photo_id = self.database.add_person_photo_from_file(
                            person_id, 
                            file_path, 
                            is_primary=is_primary
                        )
                        
                        if photo_id:
                            # Обучаем модель
                            pil_image = self.database.get_photo_as_image(photo_id)
                            if pil_image and self.recognizer.train_from_pil(pil_image, person_data, photo_id):
                                # Сохраняем эмбеддинг
                                embedding = self.recognizer.extract_embedding_from_pil(pil_image)
                                if embedding is not None:
                                    self.database.update_photo_embedding(photo_id, embedding)
                                trained_count += 1
                            else:
                                error_count += 1
                        else:
                            error_count += 1
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Ошибка обработки {filename}: {e}")
            
            messagebox.showinfo("Групповое обучение", 
                               f"Обучение завершено!\nУспешно: {trained_count}\nОшибок: {error_count}")
            
            self.refresh_database()
            self.update_stats()
            self.update_model_info()
            
        except Exception as e:
            logger.error(f"Ошибка группового обучения: {e}")
            messagebox.showerror("Ошибка", f"Ошибка группового обучения: {e}")
            self.log(f"Ошибка группового обучения: {e}")

    def export_embeddings(self):
        """Экспорт эмбеддингов в файл JSON"""
        file_path = filedialog.asksaveasfilename(
            title="Экспорт эмбеддингов",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        
        if file_path:
            try:
                embeddings_data = []
                for i in range(len(self.recognizer.known_embeddings)):
                    embeddings_data.append({
                        'person_id': self.recognizer.known_ids[i],
                        'photo_id': self.recognizer.known_photo_ids[i],
                        'embedding': self.recognizer.known_embeddings[i].tolist(),
                        'name': self.recognizer.known_names[i]
                    })
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(embeddings_data, f, indent=2, ensure_ascii=False)
                
                messagebox.showinfo("Успех", f"Экспортировано {len(embeddings_data)} эмбеддингов")
                self.log(f"Экспорт эмбеддингов: {len(embeddings_data)} записей")
            except Exception as e:
                logger.error(f"Ошибка экспорта: {e}")
                messagebox.showerror("Ошибка", f"Ошибка экспорта: {e}")
                self.log(f"Ошибка экспорта эмбеддингов: {e}")

    def import_embeddings(self):
        """Импорт эмбеддингов из файла JSON"""
        file_path = filedialog.askopenfilename(
            title="Импорт эмбеддингов",
            filetypes=[("JSON files", "*.json")]
        )
        
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    embeddings_data = json.load(f)
                
                imported_count = 0
                for data in embeddings_data:
                    embedding = np.array(data['embedding'], dtype=np.float32)
                    person_data = {
                        'id': data['person_id'],
                        'last_name': data['name'].split(' ')[0] if ' ' in data['name'] else data['name']
                    }
                    
                    if self.recognizer.add_existing_embedding(embedding, person_data, data['photo_id']):
                        imported_count += 1
                
                messagebox.showinfo("Успех", f"Импортировано {imported_count} эмбеддингов")
                self.log(f"Импорт эмбеддингов: {imported_count} записей")
                self.update_model_info()
            except Exception as e:
                logger.error(f"Ошибка импорта: {e}")
                messagebox.showerror("Ошибка", f"Ошибка импорта: {e}")
                self.log(f"Ошибка импорта эмбеддингов: {e}")

    # === ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===

    def update_threshold(self, value):
        """Обновление порога распознавания"""
        try:
            threshold_value = float(value)
            self.recognizer.set_recognition_threshold(threshold_value)
            self.threshold_label.config(text=f"{threshold_value:.2f}")
            self.database.set_setting('recognition_threshold', str(threshold_value))
            self.log(f"Установлен порог распознавания: {threshold_value:.2f}")
        except ValueError as e:
            logger.error(f"Ошибка установки порога: {e}")
            self.log(f"Ошибка установки порога: {e}")

    def update_camera_person_list(self):
        """Обновление списка людей для выбора в камере"""
        try:
            people = self.database.get_all_people()
            person_list = ["-- Выберите человека --"]
            
            for person in people:
                name = f"{person.get('last_name', '')} {person.get('first_name', '')} (ID: {person.get('id', '')})"
                person_list.append(name)
            
            self.camera_person_combo['values'] = person_list
            if person_list:
                self.camera_person_combo.current(0)
        except Exception as e:
            logger.error(f"Ошибка обновления списка людей для камеры: {e}")
            self.log(f"Ошибка обновления списка людей для камеры: {e}")

    def on_camera_person_selected(self, event):
        """Обработка выбора человека для камеры"""
        selection = self.camera_person_combo.get()
        if selection and selection != "-- Выберите человека --":
            try:
                person_id = int(selection.split('ID: ')[1].rstrip(')'))
                self.current_person_id = person_id
                self.log(f"Выбран человек для съемки: {selection}")
            except (IndexError, ValueError) as e:
                self.current_person_id = None
                logger.error(f"Ошибка выбора человека: {e}")
                self.log(f"Ошибка выбора человека: {e}")

    def log(self, message):
        """Добавление сообщения в лог"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)
        except Exception as e:
            logger.error(f"Ошибка логирования: {e}")

    def update_stats(self):
        """Обновление статистики системы"""
        try:
            stats = self.database.get_database_stats()
            
            total_people = stats.get('total_people', 0)
            with_embeddings = stats.get('with_embeddings', 0)
            total_photos = stats.get('total_photos', 0)
            total_sessions = stats.get('total_sessions', 0)
            avg_confidence = self.safe_float_format(stats.get('avg_confidence', 0.0), "{:.2%}")
            db_size = stats.get('db_size_mb', 0)
            
            stats_text = f"""📊 Статистика системы KaleidoID:

👥 Людей в базе: {total_people}
🎯 С обученными лицами: {with_embeddings}
🖼️ Всего фотографий: {total_photos}
🔍 Распознаваний: {total_sessions}
📈 Средняя точность: {avg_confidence}
💾 Размер базы: {db_size} MB

💡 Статус: {"✅ Готов к работе" if with_embeddings > 0 else "❌ Требуется обучение"}
"""
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, stats_text)
            
        except Exception as e:
            logger.error(f"Ошибка обновления статистики: {e}")
            self.log(f"Ошибка обновления статистики: {e}")

    def update_model_info(self):
        """Обновление информации о модели"""
        try:
            model_info = self.recognizer.get_model_info()
            
            loaded_embeddings = model_info.get('loaded_embeddings', 0)
            unique_people = model_info.get('unique_people', 0)
            recognition_threshold = model_info.get('recognition_threshold', 0.6)
            embedding_size = model_info.get('embedding_size', 0)
            cache_size = model_info.get('cache_size', 0)
            status = model_info.get('status', 'needs_training')
            
            # Обновляем статус в статусбаре
            status_text = "✅ Готова" if status == 'ready' else "❌ Требует обучения"
            self.model_status_var.set(f"Модель: {loaded_embeddings} эмбеддингов ({status_text})")
            
            info_text = f"""🤖 KaleidoID Face Recognition

📥 Загружено эмбеддингов: {loaded_embeddings}
👥 Уникальных людей: {unique_people}
🎯 Порог распознавания: {recognition_threshold:.2f}
📐 Размер эмбеддинга: {embedding_size} точек
💾 Кэш: {cache_size} записей

🛠️ Используемые модели:
• MediaPipe Face Detection
• MediaPipe Face Mesh (468 landmarks)

💡 Статус: {"✅ Готов к работе" if status == 'ready' else "❌ Требуется обучение"}
"""
            self.model_info_text.delete(1.0, tk.END)
            self.model_info_text.insert(1.0, info_text)
            
        except Exception as e:
            logger.error(f"Ошибка обновления информации модели: {e}")
            self.log(f"Ошибка обновления информации модели: {e}")

    def update_analytics(self):
        """Обновление аналитики системы"""
        try:
            stats = self.database.get_database_stats()
            model_info = self.recognizer.get_model_info()
            
            analytics_text = f"""📈 Аналитика системы KaleidoID

ОБЩАЯ СТАТИСТИКА:
• Людей в базе: {stats.get('total_people', 0)}
• Фотографий: {stats.get('total_photos', 0)}
• Сессий распознавания: {stats.get('total_sessions', 0)}
• Средняя точность: {self.safe_float_format(stats.get('avg_confidence', 0), '{:.2%}')}

МОДЕЛЬ РАСПОЗНАВАНИЯ:
• Загружено эмбеддингов: {model_info.get('loaded_embeddings', 0)}
• Уникальных людей: {model_info.get('unique_people', 0)}
• Порог распознавания: {model_info.get('recognition_threshold', 0.6):.2f}

ПРОИЗВОДИТЕЛЬНОСТЬ:
• Размер базы данных: {stats.get('db_size_mb', 0)} MB
• Эмбеддингов в кэше: {model_info.get('cache_size', 0)}

РЕКОМЕНДАЦИИ:
{"• ✅ Система готова к работе" if model_info.get('loaded_embeddings', 0) > 0 else "• ❌ Требуется обучение модели"}
{"• 📈 Хорошая точность распознавания" if stats.get('avg_confidence', 0) > 0.7 else "• ⚠️ Низкая точность, проверьте настройки"}
{"• 💾 Размер базы в норме" if stats.get('db_size_mb', 0) < 100 else "• 🚨 Большой размер базы, рассмотрите очистку"}
"""
            self.analytics_text.delete(1.0, tk.END)
            self.analytics_text.insert(1.0, analytics_text)
            
        except Exception as e:
            logger.error(f"Ошибка обновления аналитики: {e}")
            self.log(f"Ошибка обновления аналитики: {e}")

    def show_context_menu(self, event):
        """Показать контекстное меню для таблицы"""
        item = self.database_tree.identify_row(event.y)
        if item:
            self.database_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def edit_selected_person(self):
        """Редактирование выбранной записи"""
        selected = self.database_tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите запись для редактирования")
            return
        
        item = selected[0]
        person_id = self.database_tree.item(item)["values"][0]
        self.load_person_for_edit(person_id)
        self.notebook.select(self.management_tab)

    def view_selected_person(self):
        """Просмотр выбранной записи"""
        selected = self.database_tree.selection()
        if not selected:
            return
        
        item = selected[0]
        person_id = self.database_tree.item(item)["values"][0]
        person = self.database.get_person_with_photos(person_id)
        
        if person:
            stats = self.database.get_recognition_stats(person_id)
            
            info = f"""📋 Полная информация:

👤 ФИО: {person.get('last_name', '')} {person.get('first_name', '')} {person.get('middle_name', '')}
🎂 Возраст: {person.get('age', '')}
📞 Телефон: {person.get('phone', '')}
📧 Email: {person.get('email', '')}
💼 Должность: {person.get('position', '')}
🏢 Отдел: {person.get('department', '')}
🏠 Адрес: {person.get('address', '')}

📝 Дополнительные сведения:
{person.get('notes', '')}

📊 Статистика:
🖼️ Фотографий: {len(person.get('photos', []))}
🔍 Распознаваний: {stats.get('count', 0)}
📈 Средняя точность: {self.safe_float_format(stats.get('avg_confidence', 0), '{:.2%}')}
⏰ Последний раз: {stats.get('last_seen', 'Никогда')}

📅 Дата добавления: {person.get('created_date', '')[:10]}
"""
            messagebox.showinfo(f"Информация о {person.get('last_name', '')}", info)

    def manage_person_photos(self):
        """Управление фотографиями выбранного человека"""
        selected = self.database_tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите человека для управления фото")
            return
        
        item = selected[0]
        person_id = self.database_tree.item(item)["values"][0]
        
        # Обновляем список людей и выбираем нужного
        self.refresh_people_list()
        people = self.database.get_all_people()
        for i, person in enumerate(people):
            if person['id'] == person_id:
                # Ищем в списке
                search_text = f"{person['last_name']} {person['first_name']} (ID: {person['id']})"
                for idx in range(self.people_listbox.size()):
                    if self.people_listbox.get(idx) == search_text:
                        self.people_listbox.selection_set(idx)
                        self.people_listbox.see(idx)
                        self.selected_person_id = person_id
                        self.refresh_photos_list()
                        break
                break
        
        self.notebook.select(self.photos_tab)

    def batch_train_selected_person(self):
        """Пакетное обучение для выбранного человека"""
        selected = self.database_tree.selection()
        if not selected:
            return
        
        item = selected[0]
        person_id = self.database_tree.item(item)["values"][0]
        person_name = f"{self.database_tree.item(item)['values'][1]} {self.database_tree.item(item)['values'][2]}"
        
        try:
            trained_count = self.recognizer.batch_train_person(person_id, person_name, self.database)
            
            if trained_count > 0:
                messagebox.showinfo("Успех", f"Обучено на {trained_count} фотографиях")
                self.log(f"Пакетное обучение для {person_name}: {trained_count} фото")
                self.update_model_info()
            else:
                messagebox.showwarning("Предупреждение", "Нет фотографий для обучения или они уже обучены")
        except Exception as e:
            logger.error(f"Ошибка обучения: {e}")
            messagebox.showerror("Ошибка", f"Ошибка обучения: {e}")
            self.log(f"Ошибка обучения выбранного человека: {e}")

    def export_selected_person(self):
        """Экспорт данных выбранного человека"""
        selected = self.database_tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите человека для экспорта")
            return
        
        item = selected[0]
        person_id = self.database_tree.item(item)["values"][0]
        self.export_person_data(person_id)

    def export_current_person(self):
        """Экспорт данных текущего человека"""
        if not self.current_person_id:
            messagebox.showwarning("Предупреждение", "Нет активного человека для экспорта")
            return
        
        self.export_person_data(self.current_person_id)

    def export_person_data(self, person_id):
        """Экспорт данных человека в папку"""
        try:
            export_dir = self.database.export_person_data(person_id)
            if export_dir:
                messagebox.showinfo("Успех", f"Данные экспортированы в:\n{export_dir}")
                self.log(f"Экспорт данных человека ID: {person_id}")
            else:
                messagebox.showerror("Ошибка", "Не удалось экспортировать данные")
        except Exception as e:
            logger.error(f"Ошибка экспорта: {e}")
            messagebox.showerror("Ошибка", f"Ошибка экспорта: {e}")
            self.log(f"Ошибка экспорта человека {person_id}: {e}")

    def delete_selected_person(self):
        """Удаление выбранной записи"""
        selected = self.database_tree.selection()
        if not selected:
            return
        
        item = selected[0]
        person_id = self.database_tree.item(item)["values"][0]
        person_name = f"{self.database_tree.item(item)['values'][1]} {self.database_tree.item(item)['values'][2]}"
        
        if messagebox.askyesno("Подтверждение", f"Удалить {person_name}?\n\nВсе фотографии также будут удалены."):
            try:
                if self.database.delete_person(person_id):
                    messagebox.showinfo("Успех", "Запись удалена")
                    self.log(f"Удалена запись: {person_name}")
                    self.refresh_database()
                    self.update_stats()
                    self.update_camera_person_list()
                    if self.current_person_id == person_id:
                        self.new_person()
                else:
                    messagebox.showerror("Ошибка", "Не удалось удалить запись")
            except Exception as e:
                logger.error(f"Ошибка удаления: {e}")
                messagebox.showerror("Ошибка", f"Ошибка удаления: {e}")
                self.log(f"Ошибка удаления записи: {e}")

    def delete_current_person(self):
        """Удаление текущей записи в форме"""
        if not self.current_person_id:
            messagebox.showwarning("Предупреждение", "Нет активной записи для удаления")
            return
        
        person = self.database.get_person(self.current_person_id)
        if person:
            person_name = f"{person.get('last_name', '')} {person.get('first_name', '')}"
            if messagebox.askyesno("Подтверждение", f"Удалить {person_name}?\n\nВсе фотографии также будут удалены."):
                try:
                    if self.database.delete_person(self.current_person_id):
                        messagebox.showinfo("Успех", "Запись удалена")
                        self.log(f"Удалена запись: {person_name}")
                        self.refresh_database()
                        self.update_stats()
                        self.update_camera_person_list()
                        self.new_person()
                    else:
                        messagebox.showerror("Ошибка", "Не удалось удалить запись")
                except Exception as e:
                    logger.error(f"Ошибка удаления: {e}")
                    messagebox.showerror("Ошибка", f"Ошибка удаления: {e}")
                    self.log(f"Ошибка удаления текущей записи: {e}")

    def reload_embeddings(self):
        """Перезагрузка эмбеддингов из базы данных"""
        try:
            count = self.recognizer.load_embeddings_from_database(self.database)
            messagebox.showinfo("Успех", f"Загружено {count} эмбеддингов")
            self.log(f"Перезагружено {count} эмбеддингов")
            self.update_model_info()
        except Exception as e:
            logger.error(f"Ошибка загрузки эмбеддингов: {e}")
            messagebox.showerror("Ошибка", f"Ошибка загрузки эмбеддингов: {e}")
            self.log(f"Ошибка перезагрузки эмбеддингов: {e}")

    def show_model_stats(self):
        """Показать статистику модели"""
        model_info = self.recognizer.get_model_info()
        stats = self.database.get_database_stats()
        
        loaded_embeddings = model_info.get('loaded_embeddings', 0)
        unique_people = model_info.get('unique_people', 0)
        recognition_threshold = model_info.get('recognition_threshold', 0.6)
        total_sessions = stats.get('total_sessions', 0)
        avg_confidence = self.safe_float_format(stats.get('avg_confidence', 0.0), "{:.2%}")
        total_people = stats.get('total_people', 0)
        with_embeddings = stats.get('with_embeddings', 0)
        
        stats_text = f"""📊 Статистика модели KaleidoID:

🤖 Загружено эмбеддингов: {loaded_embeddings}
👥 Уникальных людей: {unique_people}
🎯 Порог распознавания: {recognition_threshold:.2f}
🔍 Всего распознаваний: {total_sessions}
📈 Средняя уверенность: {avg_confidence}

💾 В базе данных:
👥 Людей: {total_people}
🎯 С эмбеддингами: {with_embeddings}

💡 Рекомендации:
{"• ✅ Модель готова к работе" if loaded_embeddings > 0 else "• ❌ Требуется обучение модели"}
{"• 📈 Хорошая производительность" if loaded_embeddings < 1000 else "• ⚠️ Большое количество эмбеддингов может замедлить работу"}
"""
        messagebox.showinfo("Статистика модели", stats_text)

    def cleanup_old_sessions(self):
        """Очистка старых сессий распознавания"""
        if messagebox.askyesno("Подтверждение", "Очистить старые сессии распознавания (старше 30 дней)?"):
            try:
                deleted_count = self.database.cleanup_old_sessions()
                messagebox.showinfo("Успех", f"Удалено {deleted_count} старых сессий")
                self.log(f"Очистка сессий: удалено {deleted_count} записей")
            except Exception as e:
                logger.error(f"Ошибка очистки сессий: {e}")
                messagebox.showerror("Ошибка", f"Ошибка очистки сессий: {e}")
                self.log(f"Ошибка очистки сессий: {e}")

    def backup_database(self):
        """Создание резервной копии базы данных"""
        try:
            backup_path = self.database.backup_database()
            if backup_path:
                messagebox.showinfo("Успех", f"Резервная копия создана:\n{backup_path}")
                self.log(f"Создана резервная копия: {backup_path}")
            else:
                messagebox.showerror("Ошибка", "Не удалось создать резервную копию")
        except Exception as e:
            logger.error(f"Ошибка создания бэкапа: {e}")
            messagebox.showerror("Ошибка", f"Ошибка создания бэкапа: {e}")
            self.log(f"Ошибка создания бэкапа: {e}")

    def load_camera_settings(self):
        """Загрузка настроек камеры"""
        try:
            # Загружаем порог распознавания
            threshold = self.database.get_setting('recognition_threshold', '0.75')
            self.threshold_var.set(float(threshold))
            self.threshold_label.config(text=threshold)
            
            # Загружаем настройки отображения
            show_landmarks = self.database.get_setting('show_landmarks', '1') == '1'
            self.show_landmarks_var.set(show_landmarks)
            
            show_connections = self.database.get_setting('show_connections', '1') == '1'
            self.show_connections_var.set(show_connections)
            
        except Exception as e:
            logger.error(f"Ошибка загрузки настроек камеры: {e}")
            self.log(f"Ошибка загрузки настроек камеры: {e}")

    def show_settings(self):
        """Показать диалог настроек системы"""
        try:
            settings_window = tk.Toplevel(self.root)
            settings_window.title("Настройки KaleidoID")
            settings_window.geometry("500x400")
            settings_window.transient(self.root)
            settings_window.grab_set()
            
            # Центрирование окна
            settings_window.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() - settings_window.winfo_width()) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - settings_window.winfo_height()) // 2
            settings_window.geometry(f"+{x}+{y}")
            
            # Настройки камеры
            camera_frame = ttk.LabelFrame(settings_window, text="Настройки камеры", padding="10")
            camera_frame.pack(fill=tk.X, padx=10, pady=10)
            
            ttk.Label(camera_frame, text="ID камеры:").grid(row=0, column=0, sticky=tk.W, pady=5)
            camera_var = tk.StringVar(value=self.database.get_setting('camera_id', '0'))
            ttk.Entry(camera_frame, textvariable=camera_var).grid(row=0, column=1, sticky=tk.EW, pady=5, padx=(10, 0))
            
            # Настройки распознавания
            recognition_frame = ttk.LabelFrame(settings_window, text="Настройки распознавания", padding="10")
            recognition_frame.pack(fill=tk.X, padx=10, pady=10)
            
            ttk.Label(recognition_frame, text="Минимальная уверенность детекции:").grid(row=0, column=0, sticky=tk.W, pady=5)
            detection_var = tk.StringVar(value=self.database.get_setting('min_detection_confidence', '0.5'))
            ttk.Entry(recognition_frame, textvariable=detection_var).grid(row=0, column=1, sticky=tk.EW, pady=5, padx=(10, 0))
            
            ttk.Label(recognition_frame, text="Автосохранение эмбеддингов:").grid(row=1, column=0, sticky=tk.W, pady=5)
            auto_save_var = tk.BooleanVar(value=self.database.get_setting('auto_save_embeddings', '1') == '1')
            ttk.Checkbutton(recognition_frame, variable=auto_save_var).grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
            
            # Кнопки
            button_frame = ttk.Frame(settings_window)
            button_frame.pack(fill=tk.X, padx=10, pady=10)
            
            def save_settings():
                try:
                    self.database.set_setting('camera_id', camera_var.get())
                    self.database.set_setting('min_detection_confidence', detection_var.get())
                    self.database.set_setting('auto_save_embeddings', '1' if auto_save_var.get() else '0')
                    
                    # Обновляем распознаватель
                    self.recognizer.min_detection_confidence = float(detection_var.get())
                    
                    messagebox.showinfo("Успех", "Настройки сохранены")
                    settings_window.destroy()
                    self.log("Настройки системы обновлены")
                    
                except Exception as e:
                    logger.error(f"Ошибка сохранения настроек: {e}")
                    messagebox.showerror("Ошибка", f"Ошибка сохранения настроек: {e}")
            
            ttk.Button(button_frame, text="💾 Сохранить", command=save_settings).pack(side=tk.RIGHT, padx=(10, 0))
            ttk.Button(button_frame, text="❌ Отмена", command=settings_window.destroy).pack(side=tk.RIGHT)
            
            settings_window.columnconfigure(1, weight=1)
            
        except Exception as e:
            logger.error(f"Ошибка открытия настроек: {e}")
            messagebox.showerror("Ошибка", f"Ошибка открытия настроек: {e}")

    def show_system_stats(self):
        """Показать расширенную статистику системы"""
        self.update_analytics()
        self.notebook.select(self.analytics_tab)

    def refresh_all(self):
        """Полное обновление всех данных"""
        try:
            self.refresh_database()
            self.refresh_people_list()
            self.update_stats()
            self.update_model_info()
            self.update_analytics()
            self.update_camera_person_list()
            self.log("Все данные обновлены")
        except Exception as e:
            logger.error(f"Ошибка полного обновления: {e}")
            self.log(f"Ошибка полного обновления: {e}")

    def on_closing(self):
        """Обработка закрытия приложения"""
        if messagebox.askokcancel("Выход", "Вы уверены, что хотите выйти из KaleidoID?"):
            try:
                self.stop_camera()
                if hasattr(self.recognizer, 'cleanup'):
                    self.recognizer.cleanup()
                self.root.destroy()
            except Exception as e:
                logger.error(f"Ошибка при закрытии: {e}")
                self.root.destroy()

    def run(self):
        """Запуск интерфейса"""
        try:
            # Загружаем начальные данные
            self.refresh_all()
            self.root.mainloop()
        except Exception as e:
            logger.error(f"Критическая ошибка запуска: {e}")
            messagebox.showerror("Ошибка", f"Критическая ошибка: {e}")