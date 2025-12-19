from io import BytesIO
from PIL import Image
import pytesseract
import cv2
import numpy as np
import re
from typing import Optional


class ImageToTextService:
    """Анализатор изображений для извлечения текста и определения типа ошибки"""
    async def extract_text_from_image(self, image_bytes: bytes) -> Optional[str]:
        """Извлечение текста из изображения с помощью OCR"""
        # Конвертируем bytes в изображение PIL
        image = Image.open(BytesIO(image_bytes))
        
        # Преобразуем в OpenCV формат для улучшения качества
        open_cv_image = np.array(image)
        
        # Преобразуем RGB в BGR (для OpenCV)
        if len(open_cv_image.shape) == 3:
            open_cv_image = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2BGR)
        
        # Улучшаем изображение для лучшего OCR
        gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
        
        # Применяем пороговую обработку
        _, threshold = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Конвертируем обратно в PIL Image
        enhanced_image = Image.fromarray(threshold)
        
        # Извлекаем текст с поддержкой русского и английского
        custom_config = r'--oem 3 --psm 6 -l rus'
        extracted_text = pytesseract.image_to_string(enhanced_image, config=custom_config)
        
        # Альтернативный метод для более сложных случаев
        if len(extracted_text.strip()) < 20:  # Если мало текста
            # Попробуем без улучшений
            extracted_text = pytesseract.image_to_string(image, config=custom_config)
        
        # Очистка текста
        cleaned_text = re.sub(r'\s+', ' ', extracted_text).strip()
        
        return cleaned_text

    async def analyze_error_screenshot(self, image_bytes: bytes, user_description: str = "") -> Optional[str]:
        """Анализ скриншота с ошибкой"""
        # Извлекаем текст из изображения
        ocr_result = await self.extract_text_from_image(image_bytes)
        
        if not ocr_result:
            return None
        
        extracted_text = ocr_result
        
        # Объединяем текст из OCR и описание пользователя
        full_text = f"{user_description}. {extracted_text}" if user_description else extracted_text
        
        return full_text  # Ограничиваем длину

    async def photoToText(self, bot, message):
        """Обработка скриншотов с ошибками"""
        # Скачиваем изображение
        photo = message.photo[-1]  # Берем самое большое изображение
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        
        # Конвертируем в bytes
        image_bytes = downloaded_file.read()
        
        # Анализируем изображение
        analysis_result = await self.analyze_error_screenshot(
            image_bytes,
            user_description=message.caption if message.caption else ""
        )
        
        if not analysis_result:
            return None

        return analysis_result
