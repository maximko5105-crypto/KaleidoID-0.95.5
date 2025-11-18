#!/usr/bin/env python3
"""
База данных для KaleidoID с исправленными методами
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta
from contextlib import contextmanager
import logging
from PIL import Image
import io
import sys
import numpy as np
import shutil

logger = logging.getLogger(__name__)

class KaleidoDatabase:
    """Улучшенный класс базы данных с полной реализацией методов"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            base_dir = self.get_base_path()
            self.db_path = os.path.join(base_dir, "data", "face_database.db")
        else:
            self.db_path = db_path
            
        # Создаем директорию если не существует
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_database()

    def get_base_path(self):
        """Получение базового пути"""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для подключения к БД"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Ошибка БД: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def init_database(self):
        """Инициализация базы данных с улучшенной обработкой ошибок"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Таблица людей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS people (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        last_name TEXT NOT NULL,
                        first_name TEXT NOT NULL,
                        middle_name TEXT,
                        age INTEGER,
                        position TEXT,
                        department TEXT,
                        phone TEXT,
                        email TEXT,
                        address TEXT,
                        notes TEXT,
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                ''')
                
                # Таблица фотографий
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS person_photos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        person_id INTEGER NOT NULL,
                        image_data BLOB NOT NULL,
                        image_format TEXT NOT NULL,
                        original_filename TEXT,
                        face_embedding BLOB,
                        is_primary BOOLEAN DEFAULT 0,
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (person_id) REFERENCES people (id) ON DELETE CASCADE
                    )
                ''')
                
                # Таблица сессий распознавания
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS recognition_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        person_id INTEGER,
                        recognition_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        confidence REAL,
                        camera_id TEXT,
                        FOREIGN KEY (person_id) REFERENCES people (id)
                    )
                ''')
                
                # Таблица настроек
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        description TEXT,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Индексы для производительности
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_people_names ON people(last_name, first_name)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_photos_person ON person_photos(person_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_person ON recognition_sessions(person_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_time ON recognition_sessions(recognition_time)')
                
                # Настройки по умолчанию
                self._init_default_settings(cursor)
                
                logger.info("База данных инициализирована успешно")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise

    def _init_default_settings(self, cursor):
        """Инициализация настроек по умолчанию"""
        default_settings = [
            ('recognition_threshold', '0.75', 'Порог распознавания лиц'),
            ('min_detection_confidence', '0.7', 'Минимальная уверенность детекции'),
            ('camera_id', '0', 'ID камеры по умолчанию'),
            ('auto_save_embeddings', '1', 'Автоматически сохранять эмбеддинги'),
            ('backup_interval_days', '7', 'Интервал автоматического бэкапа в днях'),
        ]
        
        for key, value, description in default_settings:
            cursor.execute('''
                INSERT OR IGNORE INTO system_settings (key, value, description)
                VALUES (?, ?, ?)
            ''', (key, value, description))

    # === МЕТОДЫ ДЛЯ РАБОТЫ С ЛЮДЬМИ ===

    def add_person(self, person_data):
        """Добавление нового человека в базу"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO people 
                    (last_name, first_name, middle_name, age, position, 
                     department, phone, email, address, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    person_data.get('last_name', ''),
                    person_data.get('first_name', ''),
                    person_data.get('middle_name', ''),
                    self._safe_int(person_data.get('age')),
                    person_data.get('position', ''),
                    person_data.get('department', ''),
                    person_data.get('phone', ''),
                    person_data.get('email', ''),
                    person_data.get('address', ''),
                    person_data.get('notes', '')
                ))
                person_id = cursor.lastrowid
                logger.info(f"Добавлен человек: {person_data.get('last_name')} {person_data.get('first_name')} (ID: {person_id})")
                return person_id
        except Exception as e:
            logger.error(f"Ошибка добавления человека: {e}")
            return None

    def update_person(self, person_id, person_data):
        """Обновление данных человека"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE people 
                    SET last_name=?, first_name=?, middle_name=?, age=?, 
                        position=?, department=?, phone=?, email=?, address=?, notes=?,
                        last_updated=CURRENT_TIMESTAMP
                    WHERE id=?
                ''', (
                    person_data.get('last_name', ''),
                    person_data.get('first_name', ''),
                    person_data.get('middle_name', ''),
                    self._safe_int(person_data.get('age')),
                    person_data.get('position', ''),
                    person_data.get('department', ''),
                    person_data.get('phone', ''),
                    person_data.get('email', ''),
                    person_data.get('address', ''),
                    person_data.get('notes', ''),
                    person_id
                ))
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Обновлен человек ID: {person_id}")
                return success
        except Exception as e:
            logger.error(f"Ошибка обновления человека {person_id}: {e}")
            return False

    def get_person(self, person_id):
        """Получение человека по ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM people WHERE id=? AND is_active=1', (person_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка получения человека {person_id}: {e}")
            return None

    def get_person_with_photos(self, person_id):
        """Получение человека со всеми фотографиями"""
        try:
            person = self.get_person(person_id)
            if person:
                person['photos'] = self.get_person_photos(person_id)
            return person
        except Exception as e:
            logger.error(f"Ошибка получения человека с фото {person_id}: {e}")
            return None

    def get_all_people(self, include_inactive=False):
        """Получение всех людей"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if include_inactive:
                    cursor.execute('SELECT * FROM people ORDER BY last_name, first_name')
                else:
                    cursor.execute('SELECT * FROM people WHERE is_active=1 ORDER BY last_name, first_name')
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения списка людей: {e}")
            return []

    def search_people(self, search_term, include_inactive=False):
        """Поиск людей по различным полям"""
        if not search_term:
            return self.get_all_people(include_inactive)
            
        search_pattern = f'%{search_term}%'
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = '''
                    SELECT * FROM people 
                    WHERE (last_name LIKE ? OR first_name LIKE ? OR 
                           middle_name LIKE ? OR position LIKE ? OR 
                           department LIKE ? OR phone LIKE ? OR 
                           email LIKE ? OR notes LIKE ?)
                '''
                if not include_inactive:
                    query += ' AND is_active=1'
                query += ' ORDER BY last_name, first_name'
                
                cursor.execute(query, (
                    search_pattern, search_pattern, search_pattern,
                    search_pattern, search_pattern, search_pattern,
                    search_pattern, search_pattern
                ))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка поиска людей: {e}")
            return []

    def delete_person(self, person_id):
        """Удаление человека (мягкое удаление)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE people SET is_active=0 WHERE id=?', (person_id,))
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Удален человек ID: {person_id}")
                return success
        except Exception as e:
            logger.error(f"Ошибка удаления человека {person_id}: {e}")
            return False

    # === МЕТОДЫ ДЛЯ РАБОТЫ С ФОТОГРАФИЯМИ ===

    def add_person_photo(self, person_id, image_data, image_format="JPEG", 
                        original_filename=None, embedding=None, is_primary=False):
        """Добавление фотографии человека"""
        try:
            # Конвертируем изображение в bytes
            if hasattr(image_data, 'save'):
                # PIL Image
                img_byte_arr = io.BytesIO()
                image_data.save(img_byte_arr, format=image_format)
                image_bytes = img_byte_arr.getvalue()
            else:
                image_bytes = image_data

            # Подготавливаем embedding
            embedding_data = self._prepare_embedding_data(embedding)

            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Если это основное фото, снимаем флаг с других
                if is_primary:
                    cursor.execute('UPDATE person_photos SET is_primary=0 WHERE person_id=?', (person_id,))
                
                cursor.execute('''
                    INSERT INTO person_photos 
                    (person_id, image_data, image_format, original_filename, face_embedding, is_primary)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (person_id, image_bytes, image_format, original_filename, embedding_data, is_primary))
                
                photo_id = cursor.lastrowid
                logger.info(f"Добавлено фото ID: {photo_id} для человека ID: {person_id}")
                return photo_id
                
        except Exception as e:
            logger.error(f"Ошибка добавления фото для человека {person_id}: {e}")
            return None

    def add_person_photo_from_file(self, person_id, file_path, is_primary=False):
        """Добавление фотографии из файла"""
        try:
            with Image.open(file_path) as img:
                original_filename = os.path.basename(file_path)
                return self.add_person_photo(
                    person_id, img, "JPEG", original_filename, is_primary=is_primary
                )
        except Exception as e:
            logger.error(f"Ошибка добавления фото из файла {file_path}: {e}")
            return None

    def get_person_photos(self, person_id):
        """Получение всех фотографий человека"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, person_id, image_format, original_filename, 
                           face_embedding, is_primary, created_date
                    FROM person_photos 
                    WHERE person_id=? 
                    ORDER BY is_primary DESC, created_date DESC
                ''', (person_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка получения фото для человека {person_id}: {e}")
            return []

    def get_photo_data(self, photo_id):
        """Получение данных фотографии"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT image_data, image_format, original_filename
                    FROM person_photos 
                    WHERE id=?
                ''', (photo_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка получения данных фото {photo_id}: {e}")
            return None

    def get_photo_as_image(self, photo_id):
        """Получение фотографии как PIL Image"""
        try:
            photo_data = self.get_photo_data(photo_id)
            if photo_data and photo_data['image_data']:
                return Image.open(io.BytesIO(photo_data['image_data']))
            return None
        except Exception as e:
            logger.error(f"Ошибка загрузки фото {photo_id} как изображения: {e}")
            return None

    def get_photo_embedding(self, photo_id):
        """Получение эмбеддинга фотографии"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT face_embedding FROM person_photos WHERE id=?', (photo_id,))
                result = cursor.fetchone()
                
                if result and result['face_embedding']:
                    return self._parse_embedding_data(result['face_embedding'])
                return None
        except Exception as e:
            logger.error(f"Ошибка получения эмбеддинга фото {photo_id}: {e}")
            return None

    def update_photo_embedding(self, photo_id, embedding):
        """Обновление эмбеддинга фотографии"""
        try:
            embedding_data = self._prepare_embedding_data(embedding)

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE person_photos 
                    SET face_embedding=?
                    WHERE id=?
                ''', (embedding_data, photo_id))
                success = cursor.rowcount > 0
                if success:
                    logger.debug(f"Обновлен эмбеддинг фото {photo_id}")
                return success
                
        except Exception as e:
            logger.error(f"Ошибка обновления эмбеддинга фото {photo_id}: {e}")
            return False

    def set_primary_photo(self, photo_id):
        """Установка фотографии как основной"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем person_id для этой фотографии
                cursor.execute('SELECT person_id FROM person_photos WHERE id=?', (photo_id,))
                result = cursor.fetchone()
                if not result:
                    return False
                    
                person_id = result['person_id']
                
                # Снимаем флаг со всех фотографий этого человека
                cursor.execute('UPDATE person_photos SET is_primary=0 WHERE person_id=?', (person_id,))
                
                # Устанавливаем флаг для указанной фотографии
                cursor.execute('UPDATE person_photos SET is_primary=1 WHERE id=?', (photo_id,))
                
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Установлено основное фото {photo_id} для человека {person_id}")
                return success
                
        except Exception as e:
            logger.error(f"Ошибка установки основного фото {photo_id}: {e}")
            return False

    def get_primary_photo(self, person_id):
        """Получение ID основной фотографии человека"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM person_photos WHERE person_id=? AND is_primary=1 LIMIT 1', (person_id,))
                result = cursor.fetchone()
                return result['id'] if result else None
        except Exception as e:
            logger.error(f"Ошибка получения основного фото для человека {person_id}: {e}")
            return None

    def delete_photo(self, photo_id):
        """Удаление фотографии"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM person_photos WHERE id=?', (photo_id,))
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"Удалено фото ID: {photo_id}")
                return success
        except Exception as e:
            logger.error(f"Ошибка удаления фото {photo_id}: {e}")
            return False

    # === МЕТОДЫ ДЛЯ СЕССИЙ РАСПОЗНАВАНИЯ ===

    def add_recognition_session(self, person_id, confidence, camera_id=None):
        """Добавление записи о сессии распознавания"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO recognition_sessions (person_id, confidence, camera_id)
                    VALUES (?, ?, ?)
                ''', (person_id, confidence, camera_id))
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка добавления сессии распознавания: {e}")
            return None

    def get_recognition_stats(self, person_id=None, days=30):
        """Получение статистики распознаваний"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if person_id:
                    # Статистика для конкретного человека
                    cursor.execute('''
                        SELECT 
                            COUNT(*) as count,
                            AVG(confidence) as avg_confidence,
                            MAX(recognition_time) as last_seen
                        FROM recognition_sessions 
                        WHERE person_id=? AND recognition_time >= datetime('now', ?)
                    ''', (person_id, f'-{days} days'))
                else:
                    # Общая статистика
                    cursor.execute('''
                        SELECT 
                            COUNT(*) as count,
                            AVG(confidence) as avg_confidence
                        FROM recognition_sessions 
                        WHERE recognition_time >= datetime('now', ?)
                    ''', (f'-{days} days',))
                
                result = cursor.fetchone()
                if result:
                    stats = dict(result)
                    # Форматируем последнее время
                    if 'last_seen' in stats and stats['last_seen']:
                        stats['last_seen'] = stats['last_seen'][:16]  # Обрезаем до минут
                    else:
                        stats['last_seen'] = 'Никогда'
                    return stats
                return {'count': 0, 'avg_confidence': 0.0, 'last_seen': 'Никогда'}
                
        except Exception as e:
            logger.error(f"Ошибка получения статистики распознавания: {e}")
            return {'count': 0, 'avg_confidence': 0.0, 'last_seen': 'Никогда'}

    def cleanup_old_sessions(self, days=30):
        """Очистка старых сессий распознавания"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM recognition_sessions 
                    WHERE recognition_time < datetime('now', ?)
                ''', (f'-{days} days',))
                deleted_count = cursor.rowcount
                logger.info(f"Очищено сессий распознавания: {deleted_count}")
                return deleted_count
        except Exception as e:
            logger.error(f"Ошибка очистки сессий: {e}")
            return 0

    # === МЕТОДЫ ДЛЯ НАСТРОЕК ===

    def get_setting(self, key, default=None):
        """Получение значения настройки"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM system_settings WHERE key = ?', (key,))
                result = cursor.fetchone()
                return result['value'] if result else default
        except Exception as e:
            logger.error(f"Ошибка получения настройки {key}: {e}")
            return default

    def set_setting(self, key, value):
        """Установка значения настройки"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO system_settings (key, value, last_updated)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (key, str(value)))
                logger.debug(f"Обновлена настройка {key} = {value}")
                return True
        except Exception as e:
            logger.error(f"Ошибка установки настройки {key}: {e}")
            return False

    # === СТАТИСТИКА И АНАЛИТИКА ===

    def get_database_stats(self):
        """Получение статистики базы данных - ИСПРАВЛЕННЫЙ МЕТОД"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Общее количество людей
                cursor.execute('SELECT COUNT(*) as count FROM people WHERE is_active=1')
                stats['total_people'] = cursor.fetchone()['count']
                
                # Количество людей с эмбеддингами
                cursor.execute('''
                    SELECT COUNT(DISTINCT p.id) as count 
                    FROM people p 
                    JOIN person_photos pp ON p.id = pp.person_id 
                    WHERE pp.face_embedding IS NOT NULL AND p.is_active=1
                ''')
                stats['with_embeddings'] = cursor.fetchone()['count']
                
                # Общее количество фотографий
                cursor.execute('SELECT COUNT(*) as count FROM person_photos')
                stats['total_photos'] = cursor.fetchone()['count']
                
                # Количество сессий распознавания
                cursor.execute('SELECT COUNT(*) as count FROM recognition_sessions')
                stats['total_sessions'] = cursor.fetchone()['count']
                
                # Средняя уверенность распознавания
                cursor.execute('SELECT AVG(confidence) as avg_confidence FROM recognition_sessions')
                avg_conf = cursor.fetchone()['avg_confidence']
                stats['avg_confidence'] = float(avg_conf) if avg_conf else 0.0
                
                # Размер базы данных
                if os.path.exists(self.db_path):
                    db_size_bytes = os.path.getsize(self.db_path)
                    stats['db_size_mb'] = round(db_size_bytes / (1024 * 1024), 2)
                else:
                    stats['db_size_mb'] = 0
                
                # Последнее обновление
                cursor.execute('SELECT MAX(last_updated) as last_update FROM people')
                last_update = cursor.fetchone()['last_update']
                stats['last_update'] = last_update if last_update else 'Никогда'
                
                return stats
                
        except Exception as e:
            logger.error(f"Ошибка получения статистики БД: {e}")
            # Возвращаем статистику по умолчанию при ошибке
            return {
                'total_people': 0,
                'with_embeddings': 0,
                'total_photos': 0,
                'total_sessions': 0,
                'avg_confidence': 0.0,
                'db_size_mb': 0,
                'last_update': 'Ошибка'
            }

    # === РЕЗЕРВНОЕ КОПИРОВАНИЕ И ЭКСПОРТ ===

    def backup_database(self):
        """Создание резервной копии базы данных"""
        try:
            base_dir = self.get_base_path()
            backup_dir = os.path.join(base_dir, "data", "backups")
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"face_database_backup_{timestamp}.db")
            
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"Создана резервная копия: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Ошибка создания резервной копии: {e}")
            return None

    def export_person_data(self, person_id):
        """Экспорт данных человека"""
        try:
            person = self.get_person_with_photos(person_id)
            if not person:
                return None
                
            base_dir = self.get_base_path()
            export_dir = os.path.join(base_dir, "data", "exports")
            os.makedirs(export_dir, exist_ok=True)
            
            person_name = f"{person.get('last_name', '')}_{person.get('first_name', '')}"
            export_path = os.path.join(export_dir, f"{person_name}_{person_id}")
            os.makedirs(export_path, exist_ok=True)
            
            # Сохраняем информацию о человеке в JSON
            info_file = os.path.join(export_path, "person_info.json")
            with open(info_file, 'w', encoding='utf-8') as f:
                # Убираем бинарные данные перед сохранением
                export_data = person.copy()
                if 'photos' in export_data:
                    for photo in export_data['photos']:
                        if 'image_data' in photo:
                            del photo['image_data']
                        if 'face_embedding' in photo:
                            del photo['face_embedding']
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            # Сохраняем фотографии
            photos_dir = os.path.join(export_path, "photos")
            os.makedirs(photos_dir, exist_ok=True)
            
            for photo in person.get('photos', []):
                photo_data = self.get_photo_data(photo['id'])
                if photo_data and photo_data['image_data']:
                    filename = photo.get('original_filename', f"photo_{photo['id']}.jpg")
                    photo_path = os.path.join(photos_dir, filename)
                    with open(photo_path, 'wb') as f:
                        f.write(photo_data['image_data'])
            
            logger.info(f"Экспортированы данные человека {person_id} в {export_path}")
            return export_path
            
        except Exception as e:
            logger.error(f"Ошибка экспорта данных человека {person_id}: {e}")
            return None

    # === ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===

    def _safe_int(self, value, default=None):
        """Безопасное преобразование в int"""
        if value is None or value == '':
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _prepare_embedding_data(self, embedding):
        """Подготовка эмбеддинга для сохранения в БД"""
        if embedding is None:
            return None
            
        try:
            if hasattr(embedding, 'tobytes'):
                return embedding.tobytes()
            elif hasattr(embedding, 'tolist'):
                return json.dumps(embedding.tolist()).encode('utf-8')
            else:
                return None
        except Exception as e:
            logger.error(f"Ошибка подготовки эмбеддинга: {e}")
            return None

    def _parse_embedding_data(self, embedding_data):
        """Парсинг эмбеддинга из данных БД"""
        if embedding_data is None:
            return None
            
        try:
            # Пробуем как numpy array
            try:
                return np.frombuffer(embedding_data, dtype=np.float32)
            except:
                # Пробуем как JSON
                try:
                    embedding_list = json.loads(embedding_data.decode('utf-8'))
                    return np.array(embedding_list, dtype=np.float32)
                except:
                    return None
        except Exception as e:
            logger.error(f"Ошибка парсинга эмбеддинга: {e}")
            return None

    def get_database_info(self):
        """Получение общей информации о базе данных"""
        stats = self.get_database_stats()
        return {
            'path': self.db_path,
            'size_mb': stats.get('db_size_mb', 0),
            'people_count': stats.get('total_people', 0),
            'photos_count': stats.get('total_photos', 0),  # ИСПРАВЛЕНО: убрана лишняя кавычка
            'sessions_count': stats.get('total_sessions', 0),
            'last_backup': self.get_setting('last_backup_time', 'Никогда')
        }  # ИСПРАВЛЕНО: добавлена закрывающая фигурная скобка

    def optimize_database(self):
        """Оптимизация базы данных"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('VACUUM')
                cursor.execute('ANALYZE')
                logger.info("База данных оптимизирована")
                return True
        except Exception as e:
            logger.error(f"Ошибка оптимизации БД: {e}")
            return False

    def __del__(self):
        """Деструктор - закрытие соединений"""
        # Не нужно явно закрывать соединения, так как используется контекстный менеджер
        pass  # ИСПРАВЛЕНО: оставлен pass, так как это допустимо