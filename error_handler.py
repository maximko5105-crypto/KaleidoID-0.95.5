"""
Утилиты для безопасной обработки ошибок в KaleidoID
"""

import logging
import traceback
from functools import wraps
from typing import Any, Tuple, Optional, Callable
import sys

logger = logging.getLogger(__name__)

class KaleidoError(Exception):
    """Базовый класс для ошибок KaleidoID"""
    pass

class FaceDetectionError(KaleidoError):
    """Ошибка обнаружения лиц"""
    pass

class FaceRecognitionError(KaleidoError):
    """Ошибка распознавания лиц"""
    pass

class DatabaseError(KaleidoError):
    """Ошибка работы с базой данных"""
    pass

class CameraError(KaleidoError):
    """Ошибка работы с камерой"""
    pass

def safe_execute(default_return=None, log_error=True):
    """
    Декоратор для безопасного выполнения функций с обработкой исключений
    
    Args:
        default_return: Значение, возвращаемое при ошибке
        log_error: Логировать ошибку или нет
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.error(f"Error in {func.__name__}: {e}")
                    logger.debug(traceback.format_exc())
                return default_return
        return wrapper
    return decorator

def safe_execute_async(default_return=None):
    """Асинхронная версия safe_execute"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                logger.debug(traceback.format_exc())
                return default_return
        return wrapper
    return decorator

def retry_on_error(max_attempts=3, delay=1.0, exceptions=(Exception,)):
    """
    Декоратор для повторного выполнения функции при ошибках
    
    Args:
        max_attempts: Максимальное количество попыток
        delay: Задержка между попытками в секундах
        exceptions: Типы исключений, при которых повторяем
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}: {e}")
            
            raise last_exception
        return wrapper
    return decorator

def safe_unpack_three(defaults=(None, 0.0, None)):
    """
    Безопасная распаковка трех значений
    
    Args:
        defaults: Кортеж значений по умолчанию
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                
                # Проверяем, что результат - кортеж/список и имеет 3 элемента
                if isinstance(result, (tuple, list)) and len(result) == 3:
                    return tuple(result)
                else:
                    logger.warning(
                        f"Function {func.__name__} returned incorrect value: "
                        f"expected 3 elements, got {len(result) if hasattr(result, '__len__') else 'non-iterable'}"
                    )
                    return defaults
                    
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                logger.debug(traceback.format_exc())
                return defaults
        return wrapper
    return decorator

def safe_unpack_two(defaults=(None, None)):
    """
    Безопасная распаковка двух значений
    
    Args:
        defaults: Кортеж значений по умолчанию
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                
                if isinstance(result, (tuple, list)) and len(result) == 2:
                    return tuple(result)
                else:
                    logger.warning(
                        f"Function {func.__name__} returned incorrect value: "
                        f"expected 2 elements, got {len(result) if hasattr(result, '__len__') else 'non-iterable'}"
                    )
                    return defaults
                    
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                logger.debug(traceback.format_exc())
                return defaults
        return wrapper
    return decorator

def handle_unpacking_errors(func):
    """
    Декоратор для обработки ошибок распаковки значений
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            error_msg = str(e)
            if "not enough values to unpack" in error_msg:
                logger.error(f"Unpacking error in {func.__name__}: {error_msg}")
                
                # Определяем сколько значений ожидалось
                if "expected 3" in error_msg:
                    logger.warning(f"Returning default values for 3-tuple unpacking in {func.__name__}")
                    return None, 0.0, None
                elif "expected 2" in error_msg:
                    logger.warning(f"Returning default values for 2-tuple unpacking in {func.__name__}")
                    return None, None
                elif "expected 4" in error_msg:
                    logger.warning(f"Returning default values for 4-tuple unpacking in {func.__name__}")
                    return None, None, None, None
                    
            # Если это другая ошибка ValueError, прокидываем её дальше
            raise e
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise e
    return wrapper

def validate_bbox(bbox: Tuple[int, int, int, int], image_shape: Tuple[int, int]) -> bool:
    """
    Проверка валидности bounding box
    
    Args:
        bbox: Кортеж (x, y, width, height)
        image_shape: Размеры изображения (height, width, channels)
    
    Returns:
        bool: True если bbox валиден
    """
    if not bbox or len(bbox) != 4:
        return False
    
    x, y, w, h = bbox
    
    # Проверяем значения на корректность
    if (x < 0 or y < 0 or w <= 0 or h <= 0 or
        x + w > image_shape[1] or y + h > image_shape[0]):
        return False
    
    return True

def validate_landmarks(landmarks: list, image_shape: Tuple[int, int]) -> bool:
    """
    Проверка валидности landmarks
    
    Args:
        landmarks: Список точек (x, y)
        image_shape: Размеры изображения
    
    Returns:
        bool: True если landmarks валидны
    """
    if not landmarks:
        return False
    
    for point in landmarks:
        if len(point) != 2:
            return False
        x, y = point
        if x < 0 or y < 0 or x >= image_shape[1] or y >= image_shape[0]:
            return False
    
    return True

def validate_embedding(embedding, expected_size: int = None) -> bool:
    """
    Проверка валидности эмбеддинга
    
    Args:
        embedding: Вектор эмбеддинга
        expected_size: Ожидаемый размер эмбеддинга
    
    Returns:
        bool: True если эмбеддинг валиден
    """
    if embedding is None:
        return False
    
    try:
        import numpy as np
        if isinstance(embedding, np.ndarray):
            if embedding.size == 0:
                return False
            if expected_size and embedding.size != expected_size:
                logger.warning(f"Embedding size mismatch: expected {expected_size}, got {embedding.size}")
                return False
        elif isinstance(embedding, (list, tuple)):
            if len(embedding) == 0:
                return False
            if expected_size and len(embedding) != expected_size:
                logger.warning(f"Embedding size mismatch: expected {expected_size}, got {len(embedding)}")
                return False
        else:
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error validating embedding: {e}")
        return False

def log_execution_time(level=logging.DEBUG):
    """
    Декоратор для логирования времени выполнения функции
    
    Args:
        level: Уровень логирования
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                logger.log(level, f"Function {func.__name__} executed in {execution_time:.3f}s")
        return wrapper
    return decorator

def deprecated(message=""):
    """
    Декоратор для пометки устаревших функций
    
    Args:
        message: Сообщение об устаревании
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.warning(f"Function {func.__name__} is deprecated. {message}")
            return func(*args, **kwargs)
        return wrapper
    return decorator

def singleton(cls):
    """
    Декоратор для реализации шаблона Singleton
    """
    instances = {}
    
    @wraps(cls)
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    
    return get_instance

def memoize(maxsize=128):
    """
    Декоратор для кэширования результатов функции
    
    Args:
        maxsize: Максимальный размер кэша
    """
    def decorator(func):
        cache = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Создаем ключ на основе аргументов
            key = str(args) + str(kwargs)
            
            if key in cache:
                return cache[key]
            
            result = func(*args, **kwargs)
            
            # Ограничиваем размер кэша
            if len(cache) >= maxsize:
                # Удаляем самый старый элемент
                cache.pop(next(iter(cache)))
            
            cache[key] = result
            return result
        
        def clear_cache():
            """Очистка кэша"""
            cache.clear()
        
        wrapper.clear_cache = clear_cache
        return wrapper
    return decorator

class ErrorContext:
    """
    Контекстный менеджер для обработки ошибок с дополнительной информацией
    """
    
    def __init__(self, operation_name: str, raise_error: bool = False, default_return=None):
        self.operation_name = operation_name
        self.raise_error = raise_error
        self.default_return = default_return
        self.success = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"Error during {self.operation_name}: {exc_val}")
            if self.raise_error:
                return False  # Пропускаем исключение дальше
            else:
                return True   # Поглощаем исключение
        
        self.success = True
        return False

# Утилиты для работы с изображениями
def validate_image(image) -> bool:
    """
    Проверка валидности изображения
    """
    try:
        if image is None:
            return False
        
        import numpy as np
        if isinstance(image, np.ndarray):
            return image.size > 0 and len(image.shape) in (2, 3)
        elif hasattr(image, 'size'):  # PIL Image
            return image.size[0] > 0 and image.size[1] > 0
        else:
            return False
    except Exception as e:
        logger.error(f"Error validating image: {e}")
        return False

def ensure_rgb(image):
    """
    Конвертация изображения в RGB формат если нужно
    """
    try:
        import numpy as np
        from PIL import Image
        
        if isinstance(image, np.ndarray):
            if len(image.shape) == 2:  # Grayscale
                return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif image.shape[2] == 4:  # RGBA
                return cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
            else:  # BGR or RGB
                return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        elif isinstance(image, Image.Image):
            if image.mode != 'RGB':
                return image.convert('RGB')
            return image
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")
    except Exception as e:
        logger.error(f"Error converting image to RGB: {e}")
        return image

# Глобальные обработчики ошибок
def setup_global_error_handling():
    """
    Настройка глобальных обработчиков ошибок
    """
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Не логируем KeyboardInterrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
    
    sys.excepthook = handle_exception

# Инициализация при импорте
setup_global_error_handling()