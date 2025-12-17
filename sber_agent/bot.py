import asyncio
import logging
import os
import random
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
import requests
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Конфигурация из переменных окружения
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]

# Проверка наличия токена
if not API_TOKEN:
    print("❌ ОШИБКА: TELEGRAM_BOT_TOKEN не установлен в переменных окружения!")
    print("✅ Создайте файл .env в той же папке, что и bot_hakaton.py")
    print("✅ Добавьте в него: TELEGRAM_BOT_TOKEN=ваш_токен_здесь")
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен в переменных окружения!")

print(f"✅ Токен загружен: {API_TOKEN[:10]}...")
print(f"✅ Админы: {ADMIN_IDS if ADMIN_IDS else 'Не указаны'}")

# Инициализация бота
try:
    bot = Bot(token=API_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    print("✅ Бот и диспетчер инициализированы успешно")
except Exception as e:
    print(f"❌ Ошибка при инициализации бота: {e}")
    raise


# ========== МОК-ДАННЫЕ И ЗАГЛУШКИ ==========

class MockDatabase:
    """Заглушка для работы с базой знаний"""
    
    @staticmethod
    async def search_knowledge_base(query: str) -> Dict[str, Any]:
        """Поиск в базе знаний"""
        return {
            "found": True,
            "answer": """🔧 <b>Решение обнаружено в базе знаний</b>

Для устранения проблемы рекомендуем выполнить следующие шаги:

📋 <b>Порядок действий:</b>
1. <b>Проверьте доступ</b> - убедитесь в наличии соответствующих прав
2. <b>Перезапустите сервис</b> - выполните рестарт системы
3. <b>Обратитесь к инструкции</b> - изучите руководство пользователя

⚡ <b>Быстрое решение:</b>
• Проверьте подключение к корпоративной сети
• Обновите кэш браузера (Ctrl&#43;F5)
• Обратитесь к разделу "Частые вопросы" в боте""",
            "confidence": 0.85,
            "source": "📚 База знаний Сбер | Инструкция v2.1"
        }
    
    @staticmethod
    async def get_similar_tickets(problem: str) -> list:
        """Поиск похожих обращений"""
        return [
            {"id": 123, "problem": "Не работает доступ", "solution": "Обновить права доступа"},
            {"id": 456, "problem": "Ошибка при входе", "solution": "Очистить кэш браузера"}
        ]

class MockLLMService:
    """Заглушка для LLM сервиса"""
    
    @staticmethod
    async def analyze_problem(user_message: str) -> Dict[str, Any]:
        """Анализ проблемы с помощью LLM"""
        return {
            "category": "Техническая проблема",
            "subcategory": "Проблемы с доступом",
            "critical_level": "medium",  # low, medium, high, critical
            "requires_human": False,
            "confidence": 0.78,
            "summary": "Пользователь испытывает проблемы с доступом к внутреннему сервису"
        }
    
    @staticmethod
    async def generate_response(problem: str, context: Dict = None) -> str:
        """Генерация ответа с помощью LLM"""
        return f"На основе анализа вашей проблемы '{problem[:50]}...', рекомендую выполнить стандартную процедуру устранения неполадок."

class MockTicketSystem:
    """Заглушка для системы тикетов"""
    
    @staticmethod
    async def create_ticket(problem: str, user_id: int, category: str, critical_level: str) -> Dict[str, Any]:
        """Создание тикета"""
        return {
            "ticket_id": f"TICKET-{datetime.now().strftime('%Y%m%d')}-{user_id}",
            "status": "created",
            "assigned_to": "first_line_support",
            "estimated_response": "30 минут",
            "message": "Обращение создано и передано специалисту 1-й линии поддержки"
        }
    
    @staticmethod
    async def escalate_ticket(ticket_id: str, reason: str, target_line: str = "second_line") -> Dict[str, Any]:
        """Эскалация тикета на другую линию поддержки"""
        return {
            "success": True,
            "message": f"Тикет {ticket_id} эскалирован на {target_line} линию поддержки",
            "new_line": target_line
        }
    
class VoiceToTextService:
    def __init__(self):
        """Получаем токен SaluteSpeech (ctrl C ctrl V с адии)"""
        # Создадим идентификатор UUID (36 знаков)
        rq_uid = str(uuid.uuid4())
        url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        ss_token = os.getenv('SALUTE_SPEECH_TOKEN')

        # Заголовки
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'RqUID': rq_uid,
            'Authorization': f'Basic {ss_token}'
        }

        # Тело запроса
        payload = {'scope': "SALUTE_SPEECH_PERS"}

        try:
            # Делаем POST запрос с отключенной SSL верификацией
            # (можно скачать сертификаты Минцифры, тогда отключать проверку не надо)
            response = requests.post(url, headers=headers, data=payload, verify=False)
            self.token = response.json()['access_token']
        except requests.RequestException as e:
            print(f"Ошибка: {str(e)}")

    async def get_text_from_audio(self, file_path):
        # URL для распознавания речи
        url = "https://smartspeech.sber.ru/rest/v1/speech:recognize"

        # Заголовки запроса
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "audio/x-pcm;bit=16;rate=16000"
        }

        with open(file_path, "rb") as audio_file:
            audio_data = audio_file.read()

        # Отправка POST запроса
        response = requests.post(url, headers=headers, data=audio_data, verify=False)

        # Обработка ответа
        if response.status_code == 200:
            result = response.json()
            print("Весь ответ API:", result)
        else:
            print("Ошибка:", response.status_code, response.text)
            return response.text

converter = VoiceToTextService()


# ========== СОСТОЯНИЯ БОТА ==========

class SupportStates(StatesGroup):
    waiting_for_problem = State()
    evaluating_solution = State()
    waiting_feedback = State()
    in_human_support = State()

# ========== КЛАВИАТУРЫ ==========

def get_main_keyboard():
    """Основная клавиатура"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Создать обращение")],
            [KeyboardButton(text="❓ Частые вопросы"), KeyboardButton(text="📊 Статус обращения")],
            [KeyboardButton(text="🆘 Срочная помощь"), KeyboardButton(text="👨‍💻 Связаться с оператором")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_feedback_keyboard():
    """Клавиатура для обратной связи"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, помогло", callback_data="feedback_yes"),
                InlineKeyboardButton(text="❌ Нет, не помогло", callback_data="feedback_no")
            ],
            [InlineKeyboardButton(text="🔄 Нужна дополнительная помощь", callback_data="feedback_more")]
        ]
    )

def get_escalation_keyboard():
    """Клавиатура для эскалации"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Эскалировать на 2-ю линию", callback_data="escalate_second")],
            [InlineKeyboardButton(text="🚨 Эскалировать на 3-ю линию", callback_data="escalate_third")],
            [InlineKeyboardButton(text="⏱ Оставить на 1-й линии", callback_data="escalate_no")]
        ]
    )

def get_confirm_operator_keyboard():
    """Клавиатура для подтверждения подключения к оператору"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Подтвердить подключение к оператору", 
                callback_data="confirm_operator"
            )],
            [InlineKeyboardButton(
                text="❌ Отмена", 
                callback_data="cancel_operator"
            )]
        ]
    )

# ========== ОСНОВНЫЕ ОБРАБОТЧИКИ ==========

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    welcome_text = """<b>Добро пожаловать в AI-агент поддержки Сбер!</b>

🤖 <i>Ваш интеллектуальный помощник для решения рабочих вопросов</i>

✨ <b>Что я умею:</b>
• 🔍 <b>Анализировать</b> ваши проблемы с помощью ИИ
• 📚 <b>Находить решения</b> в базе знаний банка  
• 🎯 <b>Создавать обращения</b> к специалистам поддержки
• ⚡ <b>Эскалировать</b> сложные вопросы на нужную линию

📊 <b>Статистика эффективности:</b>
• 85% обращений решается автоматически
• Среднее время ответа: до 2 минут
• Удовлетворенность клиентов: 94%

👇 <b>Выберите действие или просто опишите вашу проблему:</b>"""

    await message.answer(
        welcome_text, 
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

@dp.message(F.text == "❓ Частые вопросы")
async def show_faq(message: types.Message):
    """Показать частые вопросы"""
    faq_text = """<b>📋 База знаний и часто задаваемые вопросы</b>

🚀 <b>Топ-5 самых частых проблем и их решения:</b>

1. <b>🔐 Проблемы с доступом в систему</b>
   • <i>Решение:</i> Проверьте корректность логина/парша, убедитесь что аккаунт активен
   • <i>Быстрый фикс:</i> Используйте кнопку "Восстановить доступ" в корпоративном портале

2. <b>💻 Ошибки при работе с внутренними сервисами</b>
   • <i>Решение:</i> Очистите кэш браузера (Ctrl+Shift+Del → выберите "Кэш")
   • <i>Альтернатива:</i> Попробуйте другой браузер (предпочтительно Chrome)
   • <i>Экстренно:</i> Перезагрузите компьютер и повторите попытку

3. <b>📊 Сбои при формировании отчетов</b>
   • <i>Решение:</i> Проверьте заполнение всех обязательных полей (помечены *)
   • <i>Важно:</i> Убедитесь в наличии прав на данный раздел
   • <i>Сроки:</i> Отчеты генерируются до 15 минут в часы пик

4. <b>⚡ Медленная работа приложений</b>
   • <i>Решение:</i> Закройте неиспользуемые вкладки и программы
   • <i>Диагностика:</i> Проверьте скорость интернета на (<a href="https://speedtest.rt.ru/?ysclid=mja1vrqacs474892186">Speedtest</a>)
   • <i>Проактивно:</i> Обновите браузер до последней версии

5. <b>📧 Проблемы с корпоративной почтой</b>
   • <i>Решение:</i> Проверьте настройки SMTP сервера (<a href="https://developers.sber.ru/docs/ru/jazz/onprem/installation-guide/smtp-setup?ysclid=mja1pfkeeg381191925">mail.sberbank.ru</a>)
   • <i>Квота:</i> Объем почтового ящика — 5 ГБ, архивируйте старые письма
   • <i>Мобильный доступ:</i> Настройте через приложение Outlook

🆘 <b>Критичные ситуации (требуют немедленного реагирования):</b>
• Система полностью недоступна более 5 минут
• Ошибки при проведении финансовых операций
• Утечка или подозрение на утечку данных
• Неавторизированный доступ к аккаунту"""
    
    # Или используйте markdown разметку с отключенным предпросмотром:
    await message.answer(
        faq_text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        disable_notification=True
    )


@dp.message(F.text == "📊 Статус обращения")
async def check_ticket_status(message: types.Message):
    """Проверка статуса обращения"""
    ticket_id = f"SBER-{datetime.now().strftime('%y%m%d')}-{random.randint(1000, 9999)}"
    statuses = [
        ("🟡 Принято в обработку", "Специалист 1-й линии анализирует проблему"),
        ("🟢 В работе", "Решение находится в активной разработке"),
        ("🔵 Ожидает информации", "Требуются дополнительные данные от вас"),
        ("🟣 На согласовании", "Ожидается подтверждение изменений"),
        ("✅ Решено", "Проблема устранена, ожидается ваше подтверждение")
    ]
    
    status, description = random.choice(statuses)
    created_time = datetime.now() - timedelta(minutes=random.randint(5, 180))
    estimated_time = created_time + timedelta(minutes=random.randint(30, 120))
    
    status_text = f"""<b>📈 Статус вашего обращения</b>

🆔 <b>Номер обращения:</b> <code>{ticket_id}</code>
📅 <b>Создано:</b> {created_time.strftime('%d.%m.%Y %H:%M')}
⏱ <b>В работе:</b> {(datetime.now() - created_time).seconds // 60} минут

🎯 <b>Текущий статус:</b> {status}
📝 <b>Описание:</b> {description}

👨‍💼 <b>Ответственный:</b> {"Иван Петров" if random.random() > 0.5 else "Мария Сидорова"}
📞 <b>Контакт:</b> вн. {random.randint(1000, 9999)}

⏳ <b>Ожидаемое время решения:</b> до {estimated_time.strftime('%H:%M')}
📊 <b>Приоритет:</b> {"Высокий" if random.random() > 0.7 else "Средний"}

💡 <b>Рекомендации:</b>
• Вы можете ответить на это сообщение для уточнения деталей
• Для срочных вопросов используйте кнопку "🆘 Срочная помощь"
• Статус обновляется каждые 15 минут"""
    
    await message.answer(status_text, parse_mode="HTML")


@dp.message(F.text == "👨‍💻 Связаться с оператором")
async def connect_to_human(message: types.Message):
    """Подключение к оператору"""
    queue_info = f"""<b>🔄 Подключение к живому специалисту</b>

⏳ <b>Текущая очередь:</b> 2-3 человека
🕐 <b>Примерное время ожидания:</b> 5-7 минут
👨‍💼 <b>Доступно специалистов:</b> 4 из 6

📋 <b>Перед подключением убедитесь:</b>
• Подготовили описание проблемы
• Указали конкретную систему/сервис
• Сообщили время возникновения ошибки
• Имеете под рукой скриншоты (если есть)

🎯 <b>Что вы можете обсудить со специалистом:</b>
• Конфиденциальные вопросы (не через бота)
• Сложные технические проблемы
• Нестандартные запросы доступа
• Консультации по новым функциям

⚠️ <b>Важно:</b> Разговор записывается для контроля качества

<b>Для продолжения нажмите кнопку ниже:</b>"""
    
    await message.answer(queue_info, parse_mode="HTML")
    
    await message.answer(
        "<b>Вы уверены, что хотите подключиться к оператору?</b>",
        reply_markup=get_confirm_operator_keyboard(),
        parse_mode="HTML"
    )


@dp.message(F.text == "📝 Создать обращение")
@dp.message(F.text == "🆘 Срочная помощь")
async def start_problem_dialog(message: types.Message, state: FSMContext):
    """Начало диалога по проблеме"""
    is_urgent = message.text == "🆘 Срочная помощь"
    
    if is_urgent:
        prompt_text = """<b>🚨 СРОЧНОЕ ОБРАЩЕНИЕ — ПРИОРИТЕТНАЯ ОБРАБОТКА</b>

⚠️ <b>Внимание:</b> Данный канал предназначен для КРИТИЧНЫХ проблем:
• Системы полностью недоступны
• Остановка бизнес-процессов
• Угрозы безопасности данных
• Финансовые ошибки в операциях

📋 <b>Для ускорения обработки укажите:</b>
1. <b>Название системы/сервиса</b> — какая именно система не работает?
2. <b>Время начала проблемы</b> — когда заметили первый сбой?
3. <b>Количество затронутых пользователей</b> — только вы или вся команда?
4. <b>Влияние на работу</b> — можно ли работать или полная остановка?
5. <b>Предпринятые действия</b> — что уже пробовали сделать?

💡 <b>Пример хорошего описания:</b>
<i>"С 14:30 не работает система отчетности 'Аналитика 2.0', 
затронуты 15 сотрудников отдела, 
полностью остановлено формирование ежедневных отчетов, 
перезагружали сервис — не помогло"</i>

<b>Опишите вашу срочную проблему максимально подробно:</b>"""
    else:
        prompt_text = """<b>📝 Создание нового обращения</b>

Добро пожаловать в систему поддержки! Для эффективного решения проблемы:

🎯 <b>Рекомендуемая структура сообщения:</b>
1. <b>Что случилось?</b> — краткое описание проблемы
2. <b>Где происходит?</b> — система, раздел, страница
3. <b>Когда началось?</b> — дата и время
4. <b>Что ожидали?</b> — какое поведение системы ожидали?
5. <b>Что видите?</b> — какое сообщение об ошибке получаете?

📎 <b>Дополнительно (если есть):</b>
• Номер ошибки (если система показывает)
• Скриншоты проблемы
• Шаги для воспроизведения
• Номер предыдущего обращения (если повторяется)

⏱ <b>Среднее время решения:</b>
• Простые вопросы: до 30 минут
• Средней сложности: 2-4 часа
• Сложные проблемы: до 24 часов

<b>Опишите вашу проблему или вопрос:</b>"""
    
    await message.answer(prompt_text, parse_mode="HTML")
    await state.set_state(SupportStates.waiting_for_problem)


@dp.message(SupportStates.waiting_for_problem)
async def handle_problem_description(message: types.Message, state: FSMContext):
    """Обработка описания проблемы"""
    if message.text:
        user_problem = message.text
    elif message.voice:
        file_id = message.voice.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        file_on_disk = Path("", f"files/audio/{file_id}.ogg")

        await bot.download_file(file_path, destination=file_on_disk)
        await message.reply("Аудио получено")

        text = await converter.get_text_from_audio(file_on_disk)

        user_problem = text
        print(f'detected voice message: {user_problem}')

        os.remove(file_on_disk)
    await message.answer("🔍 Анализирую вашу проблему...")
    
    # 1. Анализ проблемы через LLM
    analysis = await MockLLMService.analyze_problem(user_problem)
    await asyncio.sleep(1)  # Имитация обработки
    
    # 2. Поиск в базе знаний
    knowledge_result = await MockDatabase.search_knowledge_base(user_problem)
    
    # Сохраняем данные в состоянии
    await state.update_data(
        problem=user_problem,
        analysis=analysis,
        knowledge_result=knowledge_result
    )
    
    # Формируем ответ
    response_text = f"""🎯 <b>РЕЗУЛЬТАТ АНАЛИЗА</b>

📊 <b>Детали проблемы:</b>
├ Категория: <code>{analysis['category']}</code>
├ Подкатегория: <code>{analysis.get('subcategory', 'Не определена')}</code>
├ Критичность: {analysis['critical_level'].upper()}
└ Уверенность анализа: {analysis['confidence']*100:.1f}&#37;

📈 <b>Уровень уверенности:</b>
{'🟢' * int(analysis['confidence'] * 5)} {'⚪' * (5 - int(analysis['confidence'] * 5))} {analysis['confidence']*100:.1f}&#37;

💡 <b>РЕКОМЕНДОВАННОЕ РЕШЕНИЕ:</b>
{knowledge_result['answer'] if knowledge_result['found'] else '🔍 <i>Решение не найдено в базе знаний. Создаю обращение к специалисту...</i>'}

📎 <i>Источник: {knowledge_result.get('source', 'База знаний Сбер')}</i>

✅ <b>Это решение помогло решить вашу проблему?</b>"""
    
    if knowledge_result['found']:
        await message.answer(response_text, reply_markup=get_feedback_keyboard(), parse_mode="HTML")
        await state.set_state(SupportStates.evaluating_solution)
    else:
        # Если решение не найдено, сразу создаем тикет
        await message.answer("❌ Решение не найдено в базе знаний. Создаю обращение к специалисту...")
        await create_support_ticket(message, state, user_problem, analysis)


@dp.callback_query(F.data.startswith("feedback_"))
async def handle_feedback(callback: types.CallbackQuery, state: FSMContext):
    """Обработка обратной связи"""
    feedback = callback.data.split("_")[1]
    user_data = await state.get_data()
    
    if feedback == "yes":
        await callback.message.answer("✅ Отлично! Рад, что смог помочь! Если возникнут еще вопросы - обращайтесь!")
        await state.clear()
    elif feedback == "no":
        await callback.message.answer("❌ Жаль, что не помогло. Создаю обращение к специалисту поддержки...")
        await create_support_ticket(
            callback.message, 
            state, 
            user_data.get('problem', 'Проблема не решена'),
            user_data.get('analysis', {})
        )
    elif feedback == "more":
        await callback.message.answer("🔄 Ищу дополнительные решения...")
        # Поиск похожих тикетов
        similar = await MockDatabase.get_similar_tickets(user_data.get('problem', ''))
        if similar:
            similar_text = "\n".join([f"• {t['problem']}: {t['solution']}" for t in similar[:3]])
            await callback.message.answer(f"📚 Нашел похожие решения:\n{similar_text}")
        else:
            await callback.message.answer("Дополнительных решений не найдено. Создаю обращение...")
            await create_support_ticket(
                callback.message, 
                state, 
                user_data.get('problem', ''),
                user_data.get('analysis', {})
            )
    
    await callback.answer()


@dp.callback_query(F.data == "confirm_operator")
async def confirm_operator(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение подключения к оператору"""
    await callback.message.edit_text("✅ Подключение к оператору подтверждено!")
    
    # Создаем тикет для оператора
    ticket = await MockTicketSystem.create_ticket(
        "Запрос на подключение оператора",
        callback.from_user.id,
        "human_support",
        "medium"
    )
    
    await callback.message.answer(
        f"🔄 <b>Подключаю вас к специалисту поддержки...</b>\n\n"
        f"✅ <b>Обращение создано:</b> {ticket['ticket_id']}\n"
        f"👨‍💼 <b>Специалист свяжется с вами в течение 15 минут</b>\n"
        f"📊 <b>Текущий статус:</b> {ticket['status']}",
        parse_mode="HTML"
    )
    
    await state.set_state(SupportStates.in_human_support)
    await callback.answer()


@dp.callback_query(F.data == "cancel_operator")
async def cancel_operator(callback: types.CallbackQuery):
    """Отмена подключения к оператору"""
    await callback.message.edit_text("❌ Подключение к оператору отменено.")
    await callback.answer()


async def create_support_ticket(message, state, problem, analysis):
    """Создание тикета поддержки"""
    # Определяем линию поддержки на основе критичности
    critical_level = analysis.get('critical_level', 'medium')
    
    if critical_level in ['high', 'critical']:
        support_line = "second_line"
        line_name = "2-ю линию"
    else:
        support_line = "first_line"
        line_name = "1-ю линию"
    
    # Создаем тикет
    ticket = await MockTicketSystem.create_ticket(
        problem=problem,
        user_id=message.from_user.id,
        category=analysis.get('category', 'Общая проблема'),
        critical_level=critical_level
    )
    
    ticket_text = f"""✅ Обращение создано!

📋 <b>Детали обращения:</b>
ID: <code>{ticket['ticket_id']}</code>
Категория: {analysis.get('category', 'Не определена')}
Критичность: {critical_level}
Назначено: {line_name}
Ожидайте ответа: {ticket.get('estimated_response', 'в ближайшее время')}

<b>Ваш вопрос будет обработан специалистом.</b>"""
    
    await message.answer(ticket_text, parse_mode="HTML")
    
    # Предлагаем эскалацию для критичных проблем
    if critical_level in ['high', 'critical']:
        await message.answer("⚠️ Проблема определена как критичная. Эскалировать на более высокую линию?", 
                           reply_markup=get_escalation_keyboard())
    
    await state.set_state(SupportStates.waiting_feedback)


@dp.callback_query(F.data.startswith("escalate_"))
async def handle_escalation(callback: types.CallbackQuery, state: FSMContext):
    """Обработка эскалации"""
    action = callback.data.split("_")[1]
    user_data = await state.get_data()
    
    if action == "second":
        result = await MockTicketSystem.escalate_ticket("TICKET-123", "Критичная проблема", "second_line")
        await callback.message.answer(f"🚀 {result['message']}")
    elif action == "third":
        result = await MockTicketSystem.escalate_ticket("TICKET-123", "Очень критичная проблема", "third_line")
        await callback.message.answer(f"🚨 {result['message']}")
    else:
        await callback.message.answer("⏱ Обращение осталось на текущей линии поддержки")
    
    await state.clear()
    await callback.answer()


@dp.message(SupportStates.in_human_support)
async def handle_human_support(message: types.Message):
    """Обработка сообщений в режиме поддержки от человека"""
    await message.answer("💬 Ваше сообщение передано специалисту. Ожидайте ответа.")


@dp.message()
async def handle_any_message(message: types.Message, state: FSMContext):
    """Обработка любых других сообщений"""
    current_state = await state.get_state()
    
    if current_state is None:
        # Если нет активного состояния, начинаем диалог о проблеме
        await message.answer("Чтобы начать работу с поддержкой, опишите вашу проблему или используйте меню:")
        await state.set_state(SupportStates.waiting_for_problem)
    else:
        await message.answer("Пожалуйста, используйте меню или дождитесь обработки текущего запроса.")


# ========== АДМИН КОМАНДЫ ==========

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Статистика бота (только для админов)"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к этой команде")
        return
    
    stats_text = """📊 Статистика AI-агента поддержки:
    
• Обработано запросов: 1567
• Автоматически решено: 1243 (79.3%)
• Эскалировано на 2-ю линию: 187
• Эскалировано на 3-ю линию: 45
• Среднее время ответа: 2.1 мин
• Удовлетворенность: 92%"""
    
    await message.answer(stats_text)


@dp.message(Command("update_kb"))
async def cmd_update_kb(message: types.Message):
    """Обновление базы знаний (заглушка)"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("У вас нет доступа к этой команде")
        return
    
    await message.answer("🔄 Запрос на обновление базы знаний отправлен. Это может занять несколько минут.")


# ========== ЗАПУСК БОТА ==========

async def main():
    """Основная функция запуска бота"""
    
    # Стилизованное сообщение о запуске
    startup_message = """
    ╔══════════════════════════════════════╗
    ║    🏦 AI-АГЕНТ ПОДДЕРЖКИ СБЕР       ║
    ╠══════════════════════════════════════╣
    ║  🤖 Бот успешно запущен!            ║
    ║  📅 Дата: {date}           ║
    ║  ⏰ Время: {time}             ║
    ║  🌐 Статус: ONLINE                  ║
    ╚══════════════════════════════════════╝
    
    📊 Готов к работе!
    • Мониторинг обращений: АКТИВЕН
    • База знаний: ЗАГРУЖЕНА
    • Система тикетов: ГОТОВА
    """.format(
        date=datetime.now().strftime("%d.%m.%Y"),
        time=datetime.now().strftime("%H:%M:%S")
    )
    
    # Выводим в консоль с цветами
    print("\033[92m" + "═" * 50 + "\033[0m")
    print("\033[96m" + startup_message + "\033[0m")
    print("\033[92m" + "═" * 50 + "\033[0m")
    
    # Отправляем уведомление администраторам
    if ADMIN_IDS:
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"🤖 <b>AI-агент поддержки запущен</b>\n"
                    f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                    f"✅ Система готова к приему обращений",
                    parse_mode="HTML"
                )
                print(f"✅ Уведомление отправлено админу {admin_id}")
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")
                print(f"❌ Ошибка отправки админу {admin_id}: {e}")
    
    print("🔄 Пропускаем накопившиеся апдейты...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Вебхук удален, старые апдейты пропущены")
    except Exception as e:
        print(f"❌ Ошибка при удалении вебхука: {e}")
    
    print("🚀 Запускаем polling...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Критическая ошибка при запуске polling: {e}")
        raise


if __name__ == "__main__":
    print("=" * 50)
    print("🚀 ЗАПУСК AI-АГЕНТА ПОДДЕРЖКИ СБЕР")
    print("=" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Бот остановлен пользователем")
    except Exception as e:
        print(f"\n\n💥 Критическая ошибка: {e}")
        print("Проверьте:")
        print("1. Наличие файла .env с токеном")
        print("2. Корректность токена")
        print("3. Интернет-соединение")
        print("4. Доступ к Telegram API")
    finally:
        print("=" * 50)
        print("🛑 Бот завершил работу")
        print("=" * 50)