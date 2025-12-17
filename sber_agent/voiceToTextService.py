import os
import speech_recognition  # Преобразование голоса в текст (базаримся на готовенькое от Гугла)
from pydub import AudioSegment  # Обработка аудиофайла, который присылает пользователь

class VoiceToTextService:
    async def ogg_to_wav(self, filename: str) -> str | None:
        """Конвертирует OGG аудио в WAV"""
        new_filename = filename.replace('.oga', '.wav')

        audio = AudioSegment.from_file(filename)
        audio.export(new_filename, format='wav')
        return new_filename

    async def recognize_speech(self, wav_filename: str) -> str | None:
        """Распознает речь из WAV файла."""
        recognizer = speech_recognition.Recognizer()

        try:
            with speech_recognition.WavFile(wav_filename) as source:
                wav_audio = recognizer.record(source)
            text = recognizer.recognize_google(wav_audio, language='ru-RU')
            return text
        
        except speech_recognition.UnknownValueError:
            print("Google Speech Recognition could not understand audio")
            return "Не удалось распознать речь."
        
        except speech_recognition.RequestError as e:
            print(f"Could not request results from Google service; {e}")
            return "Произошла ошибка при обращении к сервису распознавания."

    async def download_file(self, bot, file_id: str) -> str | None:
        """Скачивает файл и возвращает его локальное имя с правильным расширением."""

        file_info = await bot.get_file(file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        
        # Создаем имя файла с правильным расширением
        file_extension = os.path.splitext(file_info.file_path)[1]
        filename = os.getcwd() + f"\\{file_id}{file_extension}"
        with open(filename, 'wb') as f:
            f.write(downloaded_file.read())
        return filename
        
    async def process_media_message(self, bot, message):
        """Обрабатывает аудиофайлы и возвращает текст."""
        file_id = message.voice.file_id

        if not file_id:
            return
        
        original_filename = await self.download_file(bot, file_id)
        wav_filename = await self.ogg_to_wav(original_filename)
            
        text = await self.recognize_speech(wav_filename)
        
        # Очистка временных файлов
        if os.path.exists(original_filename):
            os.remove(original_filename)
        if os.path.exists(wav_filename):
            os.remove(wav_filename)
            
        return text
