#!/usr/bin/env python3
"""
Улучшенный распознаватель лиц для KaleidoID
"""

import cv2
import mediapipe as mp
import numpy as np
import logging
import time
from typing import List, Tuple, Optional, Dict, Any
from PIL import Image
import io

logger = logging.getLogger(__name__)

class FaceDetectionResult:
    """Результат обнаружения лица с улучшенной обработкой данных"""
    
    def __init__(self, bbox: Tuple[int, int, int, int], confidence: float, 
                 landmarks: List[Tuple[float, float]] = None, 
                 image_size: Tuple[int, int] = None):
        self.bbox = bbox  # (x, y, width, height)
        self.confidence = confidence
        self.landmarks = landmarks or []
        self.image_size = image_size
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'bbox': self.bbox,
            'confidence': self.confidence,
            'landmarks': self.landmarks,
            'image_size': self.image_size
        }
        
    def is_valid(self) -> bool:
        """Проверка валидности результата"""
        if not self.bbox or len(self.bbox) != 4:
            return False
        x, y, w, h = self.bbox
        return (x >= 0 and y >= 0 and w > 0 and h > 0 and 
                self.confidence > 0 and self.confidence <= 1.0)

class FaceRecognizer:
    """
    Улучшенный распознаватель лиц с полной реализацией методов
    """
    
    def __init__(self, min_detection_confidence: float = 0.5):
        self.min_detection_confidence = min_detection_confidence
        
        # Флаги для визуализации
        self.show_landmarks = True
        self.show_face_connections = True
        
        # Инициализация MediaPipe
        self._init_mediapipe()
        
        # Хранилище известных лиц
        self.known_embeddings: List[np.ndarray] = []
        self.known_names: List[str] = []
        self.known_ids: List[int] = []
        self.known_photo_ids: List[int] = []
        
        # Настройки
        self.recognition_threshold: float = 0.75
        self.embedding_size: int = 128
        
        logger.info("FaceRecognizer инициализирован успешно")

    def _init_mediapipe(self):
        """Инициализация MediaPipe компонентов"""
        try:
            self.mp_face_detection = mp.solutions.face_detection
            self.mp_face_mesh = mp.solutions.face_mesh
            self.mp_drawing = mp.solutions.drawing_utils
            self.mp_drawing_styles = mp.solutions.drawing_styles
            
            # Детектор лиц
            self.face_detector = self.mp_face_detection.FaceDetection(
                model_selection=1,  # 0 для близких, 1 для дальних лиц
                min_detection_confidence=self.min_detection_confidence
            )
            
            # Face Mesh для landmarks
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=10,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            
            logger.info("MediaPipe компоненты инициализированы")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации MediaPipe: {e}")
            raise

    def _safe_execute(self, func, default_return=None, *args, **kwargs):
        """Безопасное выполнение функции с обработкой исключений"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка в {func.__name__}: {e}")
            return default_return

    def detect_faces(self, image: np.ndarray) -> List[FaceDetectionResult]:
        """Обнаружение лиц в изображении с улучшенной обработкой ошибок"""
        return self._safe_execute(self._detect_faces_impl, [], image)

    def _detect_faces_impl(self, image: np.ndarray) -> List[FaceDetectionResult]:
        """Основная реализация обнаружения лиц"""
        if image is None or image.size == 0:
            logger.warning("Пустое изображение для обнаружения лиц")
            return []
            
        results = []
        image_height, image_width = image.shape[:2]
        
        try:
            # Конвертируем в RGB для MediaPipe
            if len(image.shape) == 2:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            else:
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Обнаружение лиц
            detection_results = self.face_detector.process(rgb_image)
            
            if detection_results.detections:
                for detection in detection_results.detections:
                    # Извлекаем bounding box
                    bbox = self._extract_bounding_box(detection, (image_height, image_width))
                    if not bbox:
                        continue
                    
                    # Проверяем валидность bbox
                    if not self._validate_bbox(bbox, (image_height, image_width)):
                        continue
                    
                    # Уверенность обнаружения
                    confidence = detection.score[0] if detection.score else 0.0
                    
                    # Извлекаем landmarks если нужно
                    landmarks = []
                    if self.show_landmarks:
                        landmarks = self._extract_landmarks(detection, (image_height, image_width))
                    
                    face_result = FaceDetectionResult(bbox, confidence, landmarks, (image_width, image_height))
                    results.append(face_result)
            
            logger.debug(f"Обнаружено лиц: {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"Ошибка в процессе обнаружения лиц: {e}")
            return []

    def _extract_bounding_box(self, detection, image_shape: Tuple[int, int]) -> Optional[Tuple[int, int, int, int]]:
        """Извлечение и нормализация bounding box"""
        try:
            if not detection.location_data:
                return None
                
            bbox = detection.location_data.relative_bounding_box
            h, w = image_shape
            
            x = int(bbox.xmin * w)
            y = int(bbox.ymin * h)
            width = int(bbox.width * w)
            height = int(bbox.height * h)
            
            # Добавляем отступы для лучшего захвата лица
            padding = 20
            x = max(0, x - padding)
            y = max(0, y - padding)
            width = min(w - x, width + 2 * padding)
            height = min(h - y, height + 2 * padding)
            
            return (x, y, width, height)
            
        except Exception as e:
            logger.error(f"Ошибка извлечения bounding box: {e}")
            return None

    def _extract_landmarks(self, detection, image_shape: Tuple[int, int]) -> List[Tuple[float, float]]:
        """Извлечение landmarks лица"""
        landmarks = []
        try:
            if hasattr(detection.location_data, 'relative_keypoints'):
                h, w = image_shape
                for keypoint in detection.location_data.relative_keypoints:
                    x = keypoint.x * w
                    y = keypoint.y * h
                    landmarks.append((x, y))
        except Exception as e:
            logger.debug(f"Не удалось извлечь landmarks: {e}")
            
        return landmarks

    def _validate_bbox(self, bbox: Tuple[int, int, int, int], image_shape: Tuple[int, int]) -> bool:
        """Проверка валидности bounding box"""
        if not bbox or len(bbox) != 4:
            return False
        
        x, y, w, h = bbox
        img_h, img_w = image_shape
        
        # Проверяем значения на корректность
        if (x < 0 or y < 0 or w <= 0 or h <= 0 or
            x >= img_w or y >= img_h or
            x + w > img_w or y + h > img_h):
            return False
            
        # Проверяем размеры (не слишком маленькие)
        if w < 20 or h < 20:
            return False
            
        return True

    def extract_embedding(self, image: np.ndarray) -> Optional[np.ndarray]:
        """Извлечение эмбеддинга лица из изображения"""
        return self._safe_execute(self._extract_embedding_impl, None, image)

    def _extract_embedding_impl(self, image: np.ndarray) -> Optional[np.ndarray]:
        """Основная реализация извлечения эмбеддинга"""
        if image is None or image.size == 0:
            return None
            
        # Обнаруживаем лица
        faces = self.detect_faces(image)
        if not faces:
            return None
            
        # Используем первое обнаруженное лицо
        face = faces[0]
        return self.extract_embedding_from_face(image, face)

    def extract_embedding_from_face(self, image: np.ndarray, face: FaceDetectionResult) -> Optional[np.ndarray]:
        """Извлечение эмбеддинга из обнаруженного лица"""
        return self._safe_execute(self._extract_embedding_from_face_impl, None, image, face)

    def _extract_embedding_from_face_impl(self, image: np.ndarray, face: FaceDetectionResult) -> Optional[np.ndarray]:
        """Реализация извлечения эмбеддинга из области лица"""
        if not face.is_valid():
            return None
            
        x, y, w, h = face.bbox
        
        try:
            # Вырезаем область лица
            face_roi = image[y:y+h, x:x+w]
            if face_roi.size == 0:
                return None
                
            # Создаем упрощенный эмбеддинг
            return self._create_simple_embedding(face_roi)
            
        except Exception as e:
            logger.error(f"Ошибка извлечения эмбеддинга из лица: {e}")
            return None

    def _create_simple_embedding(self, face_roi: np.ndarray) -> np.ndarray:
        """Создание упрощенного эмбеддинга на основе особенностей изображения"""
        try:
            # Ресайзим до стандартного размера
            target_size = (64, 64)
            resized = cv2.resize(face_roi, target_size)
            
            # Конвертируем в grayscale если нужно
            if len(resized.shape) == 3:
                resized = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            
            # Нормализуем значения пикселей
            normalized = resized.astype(np.float32) / 255.0
            
            # Выравниваем в вектор
            flattened = normalized.flatten()
            
            # Обрезаем или дополняем до нужного размера
            if len(flattened) > self.embedding_size:
                embedding = flattened[:self.embedding_size]
            elif len(flattened) < self.embedding_size:
                padding = np.zeros(self.embedding_size - len(flattened))
                embedding = np.concatenate([flattened, padding])
            else:
                embedding = flattened
            
            # Нормализуем эмбеддинг
            embedding_norm = np.linalg.norm(embedding)
            if embedding_norm > 0:
                embedding = embedding / embedding_norm
            
            return embedding
            
        except Exception as e:
            logger.error(f"Ошибка создания эмбеддинга: {e}")
            return np.zeros(self.embedding_size, dtype=np.float32)

    def extract_embedding_from_pil(self, pil_image: Image.Image) -> Optional[np.ndarray]:
        """Извлечение эмбеддинга из PIL Image"""
        try:
            # Конвертируем PIL в OpenCV
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            image = np.array(pil_image)
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
            return self.extract_embedding(image)
        except Exception as e:
            logger.error(f"Ошибка извлечения эмбеддинга из PIL: {e}")
            return None

    def recognize_face(self, embedding: np.ndarray) -> Tuple[Optional[int], float, Optional[int]]:
        """Распознавание лица по эмбеддингу"""
        if embedding is None or len(self.known_embeddings) == 0:
            return None, 0.0, None
            
        best_match_id = None
        best_photo_id = None
        best_similarity = 0.0
        
        try:
            for i, known_embedding in enumerate(self.known_embeddings):
                similarity = self._calculate_similarity(embedding, known_embedding)
                
                if similarity > best_similarity and similarity > self.recognition_threshold:
                    best_similarity = similarity
                    best_match_id = self.known_ids[i]
                    best_photo_id = self.known_photo_ids[i]
            
            return best_match_id, best_similarity, best_photo_id
            
        except Exception as e:
            logger.error(f"Ошибка распознавания: {e}")
            return None, 0.0, None

    def _calculate_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Вычисление схожести между эмбеддингами"""
        try:
            # Косинусное сходство для нормализованных векторов
            similarity = np.dot(emb1, emb2)
            
            # Обеспечиваем диапазон [0, 1]
            return float(max(0.0, min(1.0, (similarity + 1) / 2)))
            
        except Exception as e:
            logger.error(f"Ошибка вычисления схожести: {e}")
            return 0.0

    def recognize_face_in_image(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Распознавание всех лиц в изображении"""
        return self._safe_execute(self._recognize_face_in_image_impl, [], image)

    def _recognize_face_in_image_impl(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Основная реализация распознавания лиц в изображении"""
        results = []
        
        try:
            faces = self.detect_faces(image)
            logger.debug(f"Найдено лиц для распознавания: {len(faces)}")
            
            for face in faces:
                try:
                    embedding = self.extract_embedding_from_face(image, face)
                    if embedding is not None:
                        person_id, confidence, photo_id = self.recognize_face(embedding)
                    else:
                        person_id, confidence, photo_id = None, 0.0, None
                    
                    result = {
                        'bbox': face.bbox,
                        'detection_confidence': face.confidence,
                        'person_id': person_id,
                        'recognition_confidence': confidence,
                        'photo_id': photo_id,
                        'landmarks': face.landmarks
                    }
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Ошибка обработки отдельного лица: {e}")
                    continue
                    
            return results
            
        except Exception as e:
            logger.error(f"Ошибка в процессе распознавания лиц: {e}")
            return []

    def train_from_pil(self, pil_image: Image.Image, person_data: Dict[str, Any], 
                      photo_id: int = None) -> bool:
        """Обучение на PIL изображении"""
        try:
            embedding = self.extract_embedding_from_pil(pil_image)
            if embedding is not None:
                return self._add_embedding_to_memory(embedding, person_data, photo_id)
            return False
        except Exception as e:
            logger.error(f"Ошибка обучения на PIL изображении: {e}")
            return False

    def _add_embedding_to_memory(self, embedding: np.ndarray, 
                               person_data: Dict[str, Any], 
                               photo_id: int = None) -> bool:
        """Добавление эмбеддинга в память распознавателя"""
        try:
            self.known_embeddings.append(embedding)
            
            # Создаем отображаемое имя
            last_name = person_data.get('last_name', '')
            first_name = person_data.get('first_name', '')
            display_name = f"{last_name} {first_name}".strip()
            self.known_names.append(display_name)
            
            # ID человека
            person_id = person_data.get('id')
            if person_id is None:
                person_id = len(self.known_ids) + 1
            self.known_ids.append(person_id)
            
            # ID фотографии
            self.known_photo_ids.append(photo_id)
            
            logger.info(f"Добавлен эмбеддинг для {display_name} (ID: {person_id})")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка добавления эмбеддинга в память: {e}")
            return False

    def load_embeddings_from_database(self, database) -> int:
        """Загрузка эмбеддингов из базы данных"""
        try:
            self.clear_embeddings()
            
            loaded_count = 0
            people = database.get_all_people()
            logger.info(f"Загрузка эмбеддингов для {len(people)} людей")
            
            for person in people:
                photos = database.get_person_photos(person['id'])
                for photo in photos:
                    embedding = database.get_photo_embedding(photo['id'])
                    if embedding is not None and len(embedding) > 0:
                        display_name = f"{person.get('last_name', '')} {person.get('first_name', '')}".strip()
                        
                        self.known_embeddings.append(embedding)
                        self.known_names.append(display_name)
                        self.known_ids.append(person['id'])
                        self.known_photo_ids.append(photo['id'])
                        loaded_count += 1
                        
            logger.info(f"Загружено эмбеддингов: {loaded_count}")
            return loaded_count
            
        except Exception as e:
            logger.error(f"Ошибка загрузки эмбеддингов из базы: {e}")
            return 0

    def batch_train_person(self, person_id: int, person_name: str, database) -> int:
        """Пакетное обучение для одного человека"""
        try:
            trained_count = 0
            photos = database.get_person_photos(person_id)
            logger.info(f"Пакетное обучение для {person_name} (ID: {person_id}), фото: {len(photos)}")
            
            for photo in photos:
                try:
                    # Используем существующий эмбеддинг если есть
                    existing_embedding = database.get_photo_embedding(photo['id'])
                    
                    if existing_embedding is not None and len(existing_embedding) > 0:
                        if self.add_existing_embedding(existing_embedding, 
                                                     {'id': person_id, 'last_name': person_name}, 
                                                     photo['id']):
                            trained_count += 1
                    else:
                        # Извлекаем эмбеддинг из изображения
                        pil_image = database.get_photo_as_image(photo['id'])
                        if pil_image:
                            person_data = {'id': person_id, 'last_name': person_name, 'first_name': ''}
                            if self.train_from_pil(pil_image, person_data, photo['id']):
                                # Сохраняем эмбеддинг в базу
                                embedding = self.extract_embedding_from_pil(pil_image)
                                if embedding is not None:
                                    database.update_photo_embedding(photo['id'], embedding)
                                trained_count += 1
                                
                except Exception as e:
                    logger.error(f"Ошибка обучения на фото {photo['id']}: {e}")
                    continue
                    
            logger.info(f"Обучено на {trained_count} фото для {person_name}")
            return trained_count
            
        except Exception as e:
            logger.error(f"Ошибка пакетного обучения: {e}")
            return 0

    def add_existing_embedding(self, embedding: np.ndarray, person_data: Dict[str, Any], 
                             photo_id: int = None) -> bool:
        """Добавление существующего эмбеддинга"""
        try:
            if embedding is not None and len(embedding) > 0:
                return self._add_embedding_to_memory(embedding, person_data, photo_id)
            return False
        except Exception as e:
            logger.error(f"Ошибка добавления существующего эмбеддинга: {e}")
            return False

    def remove_embedding_by_photo_id(self, photo_id: int) -> bool:
        """Удаление эмбеддинга по ID фотографии"""
        try:
            if photo_id in self.known_photo_ids:
                index = self.known_photo_ids.index(photo_id)
                self.known_embeddings.pop(index)
                self.known_names.pop(index)
                self.known_ids.pop(index)
                self.known_photo_ids.pop(index)
                logger.info(f"Удален эмбеддинг для фото ID: {photo_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка удаления эмбеддинга: {e}")
            return False

    # === МЕТОДЫ ВИЗУАЛИЗАЦИИ ===

    def draw_detection(self, image: np.ndarray, face_info: Dict[str, Any], 
                      person_name: str = None, confidence: float = None) -> np.ndarray:
        """Отрисовка обнаруженного лица на изображении"""
        try:
            if image is None or image.size == 0:
                return image
                
            x, y, w, h = face_info['bbox']
            
            # Выбираем цвет в зависимости от результата распознавания
            if person_name and confidence is not None:
                color = (0, 255, 0)  # Зеленый для распознанных
                conf_str = f"{confidence:.2f}"
                label = f"{person_name} ({conf_str})"
            else:
                color = (0, 0, 255)  # Красный для неизвестных
                face_confidence = face_info.get('detection_confidence', 0.0)
                conf_str = f"{face_confidence:.2f}"
                label = f"Unknown ({conf_str})"
            
            # Рисуем прямоугольник вокруг лица
            cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
            
            # Рисуем подпись
            font_scale = 0.6
            thickness = 2
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
            label_y = max(y - 10, label_size[1] + 10)
            
            # Фон для текста
            cv2.rectangle(image, (x, label_y - label_size[1] - 10), 
                         (x + label_size[0], label_y), color, -1)
            cv2.putText(image, label, (x, label_y - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness)
            
            return image
            
        except Exception as e:
            logger.error(f"Ошибка отрисовки обнаружения: {e}")
            return image

    def draw_landmarks(self, image: np.ndarray, landmarks: List[Tuple[float, float]]) -> np.ndarray:
        """Отрисовка landmarks на изображении"""
        try:
            if not landmarks or image is None:
                return image
                
            for (x, y) in landmarks:
                cv2.circle(image, (int(x), int(y)), 2, (0, 255, 255), -1)
                
            return image
        except Exception as e:
            logger.error(f"Ошибка отрисовки landmarks: {e}")
            return image

    def draw_face_connections(self, image: np.ndarray, landmarks: List[Tuple[float, float]]) -> np.ndarray:
        """Отрисовка соединений между landmarks"""
        try:
            if not landmarks or image is None:
                return image
                
            # Простая отрисовка контуров - можно улучшить
            for i in range(len(landmarks) - 1):
                x1, y1 = landmarks[i]
                x2, y2 = landmarks[i + 1]
                cv2.line(image, (int(x1), int(y1)), (int(x2), int(y2)), (255, 0, 0), 1)
                
            return image
        except Exception as e:
            logger.error(f"Ошибка отрисовки соединений: {e}")
            return image

    def toggle_landmarks(self, show: bool):
        """Переключение отображения landmarks"""
        self.show_landmarks = show
        logger.info(f"Landmarks: {'включены' if show else 'отключены'}")

    def toggle_face_connections(self, show: bool):
        """Переключение отображения контуров лица"""
        self.show_face_connections = show
        logger.info(f"Контуры лица: {'включены' if show else 'отключены'}")

    # === УПРАВЛЕНИЕ МОДЕЛЬЮ ===

    def set_recognition_threshold(self, threshold: float):
        """Установка порога распознавания"""
        self.recognition_threshold = max(0.1, min(1.0, threshold))
        logger.info(f"Установлен порог распознавания: {self.recognition_threshold}")

    def clear_embeddings(self):
        """Очистка всех эмбеддингов из памяти"""
        self.known_embeddings.clear()
        self.known_names.clear()
        self.known_ids.clear()
        self.known_photo_ids.clear()
        logger.info("Эмбеддинги очищены")

    def get_model_info(self) -> Dict[str, Any]:
        """Получение информации о состоянии модели"""
        unique_people = len(set(self.known_ids)) if self.known_ids else 0
        
        return {
            'loaded_embeddings': len(self.known_embeddings),
            'unique_people': unique_people,
            'recognition_threshold': self.recognition_threshold,
            'min_detection_confidence': self.min_detection_confidence,
            'embedding_size': self.embedding_size,
            'status': 'ready' if len(self.known_embeddings) > 0 else 'needs_training',
            'cache_size': len(self.known_embeddings)
        }

    def cleanup(self):
        """Очистка ресурсов и освобождение памяти"""
        try:
            if hasattr(self, 'face_detector'):
                self.face_detector.close()
            if hasattr(self, 'face_mesh'):
                self.face_mesh.close()
            logger.info("Ресурсы распознавателя очищены")
        except Exception as e:
            logger.error(f"Ошибка очистки ресурсов: {e}")

    def __del__(self):
        """Деструктор - автоматическая очистка ресурсов"""
        self.cleanup()