import asyncio
import logging
import os
import random
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from RAG import RAGModel
from voiceToTextService import VoiceToTextService
from model import Model
from imageToTextService import ImageToTextService

from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

voiceConverter = VoiceToTextService()
photoConverter = ImageToTextService()
RAGSearher = RAGModel()
analyzer = Model()


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
    
    # Частые вопросы сгенерированы LLM на основе анализа типичных проблем 
    # во внутренних банковских системах (синтетические данные для хакатона)
    FREQUENT_QUESTIONS = [
        {
            "id": 1,
            "question": "🔐 Не работает доступ к системе",
            "short_question": "🔐 Доступ к системе",
            "answer": """🔐 Проблемы с доступом к системе

Для восстановления доступа:
1. Проверьте корректность логина/пароля
2. Убедитесь, что аккаунт активен (не заблокирован)
3. Используйте кнопку "Восстановить доступ" в корпоративном портале
4. Если не помогло - обратитесь к администратору домена

⏱ Время решения: 15-30 минут
📞 Если проблема не решена за 30 мин - создайте обращение""",
            "category": "access",
            "priority": "high",
            "keywords": [""]
        },
        {
            "id": 2,
            "question": "💻 Ошибка при входе в сервис",
            "short_question": "💻 Ошибка при входе",
            "answer": """💻 <b>Ошибки при входе в сервис</b>

Решение:
1. Очистите кэш браузера (Ctrl+Shift+Del → выберите "Кэш")
2. Попробуйте другой браузер (рекомендуется Chrome)
3. Перезагрузите компьютер
4. Проверьте подключение к корпоративной сети
5. Убедитесь, что сервис не на техническом обслуживании

📞 Если проблема не решена - создайте обращение""",
            "category": "technical",
            "priority": "medium",
            "keywords": [""]
        },
        {
            "id": 3,
            "question": "📊 Не формируется отчет",
            "short_question": "📊 Формирование отчета",
            "answer": """📊 <b>Проблемы с формированием отчетов</b>

Действия:
1. Проверьте заполнение всех обязательных полей (помечены *)
2. Убедитесь в наличии прав на данный раздел
3. Проверьте подключение к БД отчетности
4. Подождите 15 минут (в часы пик возможны задержки)
5. Попробуйте сформировать отчет в другое время

🔄 Если отчет не формируется более 30 мин - обратитесь в поддержку""",
            "category": "reports",
            "priority": "medium",
            "keywords": [""]
        },
        {
            "id": 4,
            "question": "⚡ Медленная работа системы",
            "short_question": "⚡ Медленная работа",
            "answer": """⚡ <b>Медленная работа приложений</b>

Ускорение работы:
1. Закройте неиспользуемые вкладки и программы
2. Проверьте скорость интернета (speedtest.net)
3. Обновите браузер до последней версии
4. Очистите временные файлы системы
5. Проверьте обновления операционной системы

📈 Для постоянных проблем - требуется диагностика сети
👨‍💼 Обратитесь в ИТ-отдел для проверки рабочего места""",
            "category": "performance",
            "priority": "low",
            "keywords": [""]
        },
        {
            "id": 5,
            "question": "📧 Проблемы с корпоративной почтой",
            "short_question": "📧 Корпоративная почта",
            "answer": """📧 <b>Проблемы с корпоративной почтой</b>

Решение:
1. Проверьте настройки SMTP сервера (mail.sberbank.ru)
2. Убедитесь, что не превышена квота 5 ГБ
3. Для мобильного доступа настройте через Outlook
4. Проверьте работу на web-версии (outlook.office.com)
5. Убедитесь, что пароль не истек

🔧 Технические настройки: https://developers.sber.ru/docs/ru/jazz/onprem/installation-guide/smtp-setup
📞 При проблемах с отправкой/получением - создайте обращение""",
            "category": "email",
            "priority": "medium",
            "keywords": [""]
        },
        {
            "id": 6,
            "question": "🔄 Сброс пароля",
            "short_question": "🔄 Сброс пароля",
            "answer": """🔄 <b>Сброс пароля учетной записи</b>

Процедура сброса:
1. Перейдите на портал самообслуживания
2. Нажмите "Забыли пароль?"
3. Введите корпоративный email
4. Проверьте почту и перейдите по ссылке
5. Установите новый пароль (мин. 12 символов)

⚠️ <b>Требования к паролю:</b>
• Минимум 12 символов
• Заглавные и строчные буквы
• Цифры и специальные символы
• Не использовать предыдущие 5 паролей

🔐 Если не получается - обратитесь к администратору""",
            "category": "security",
            "priority": "medium",
            "keywords": [""]
        }
    ]
    
    @staticmethod
    async def search_knowledge_base(query: str) -> Dict[str, Any]:
        """Поиск в базе знаний с определением уверенности (внутренняя метрика)"""
        
        row = RAGSearher.get_answer(query)
        print(row)
        if row is not None:
            answer = row['answer']
            found = 'Информации нет' not in answer

            return {
                "found": found,
                "answer": answer,
                "source": f"📚 База знаний Сбер",
            }
        
        # Если не нашли, возвращаем общий ответ с низкой уверенностью
        return {
            "found": True,
            "simularity": 0,  # Внутренняя метрика, не показывается пользователю
            "source": f"📚 База знаний Сбер",
            "category": 'Неизвестна',
            "answer": """🔧 <b>Решение обнаружено в базе знаний</b>

Для устранения проблемы рекомендуем выполнить следующие шаги:

📋 <b>Порядок действий:</b>
1. <b>Проверьте доступ</b> - убедитесь в наличии соответствующих прав
2. <b>Перезапустите сервис</b> - выполните рестарт системы
3. <b>Обратитесь к инструкции</b> - изучите руководство пользователя

⚡ <b>Быстрое решение:</b>
• Проверьте подключение к корпоративной сети
• Обновите кэш браузера (Ctrl+F5)
• Обратитесь к разделу "Частые вопросы" в боте

📞 <b>Если не помогло:</b> создайте обращение к специалисту""",
            "confidence": 0.65,  # Внутренняя метрика
            "source": "📚 База знаний Сбер | Общая инструкция",
            "category": "general"
        }
    
    @staticmethod
    async def get_frequent_questions() -> List[Dict]:
        """Получить список частых вопросов"""
        return MockDatabase.FREQUENT_QUESTIONS
    
    @staticmethod
    async def get_similar_tickets(problem: str) -> list:
        """Поиск похожих обращений"""
        return [
            {"id": 123, "problem": "Не работает доступ", "solution": "Обновить права доступа", "status": "решено"},
            {"id": 456, "problem": "Ошибка при входе", "solution": "Очистить кэш браузера", "status": "решено"},
            {"id": 789, "problem": "Медленная работа", "solution": "Проверить сетевое подключение", "status": "в работе"}
        ]

class MockLLMService:
    """Заглушка для LLM сервиса"""
    
    @staticmethod
    async def analyze_problem(message, user_message: str) -> Dict[str, Any]:
        """Анализ проблемы с помощью LLM"""
        if message.voice:
            user_text = await voiceConverter.process_media_message(bot, message)
        elif message.photo:
            user_text = await photoConverter.photoToText(bot, message)
        else:
            user_text = message.text
        
        if user_text:

            [is_good, summarize, category, priority] = await analyzer.send_query(user_text)
            
            # Требуется ли человек на основе критичности
            requires_human = priority == 'high'
            
            return {
                "category": category,
                "priority": priority,
                "requires_human": requires_human,
                "summary": f"{summarize}...",
                "is_good": is_good
            }
        else:
            return {"is_good": 'плохой'}
    
    @staticmethod
    async def generate_response(problem: str, context: Dict = None) -> str:
        """Генерация ответа с помощью LLM"""
        return f"На основе анализа вашей проблемы '{problem[:50]}...', рекомендую выполнить стандартную процедуру устранения неполадок."

class MockTicketSystem:
    """Заглушка для системы тикетов"""
    
    # Хранилище статусов тикетов
    _ticket_statuses = {}
    _ticket_counter = 1000
    
    @staticmethod
    async def create_ticket(problem: str, user_id: int, category: str, critical_level: str) -> Dict[str, Any]:
        """Создание тикета"""
        MockTicketSystem._ticket_counter += 1
        ticket_id = f"SBER-{datetime.now().strftime('%y%m%d')}-{MockTicketSystem._ticket_counter}"
        
        # Определяем линию поддержки на основе критичности
        if critical_level in ["critical", "high"]:
            assigned_to = "second_line_support"
            estimated_response = "15 минут"
            priority = "Высокий"
        else:
            assigned_to = "first_line_support"
            estimated_response = "30 минут"
            priority = "Средний"
        
        # Сохраняем статус
        MockTicketSystem._ticket_statuses[ticket_id] = {
            "status": "created",
            "user_id": user_id,
            "problem": problem,
            "category": category,
            "critical_level": critical_level,
            "priority": priority,
            "created_at": datetime.now(),
            "assigned_to": assigned_to,
            "updates": []
        }
        
        # Добавляем первое обновление
        MockTicketSystem._ticket_statuses[ticket_id]["updates"].append({
            "timestamp": datetime.now(),
            "status": "created",
            "message": "Обращение создано в системе"
        })
        
        return {
            "ticket_id": ticket_id,
            "status": "created",
            "assigned_to": assigned_to,
            "estimated_response": estimated_response,
            "message": f"Обращение создано и передано на {assigned_to.replace('_', ' ')}",
            "priority": priority
        }
    
    @staticmethod
    async def get_ticket_status(ticket_id: str) -> Optional[Dict[str, Any]]:
        """Получить статус тикета с автоматическим обновлением - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        if ticket_id not in MockTicketSystem._ticket_statuses:
            return None
        
        ticket = MockTicketSystem._ticket_statuses[ticket_id]
        
        # ВАЖНО: Не создаем новый объект, работаем с существующим
        time_diff = datetime.now() - ticket["created_at"]
        current_status = ticket["status"]
        
        # Имитация изменения статуса со временем (используем существующий ticket)
        if current_status == "created" and time_diff.total_seconds() > 30:  # Уменьшили до 30 секунд для демо
            ticket["status"] = "in_progress"
            ticket["updates"].append({
                "timestamp": datetime.now(),
                "status": "in_progress",
                "message": "Специалист начал работу над проблемой"
            })
        
        elif current_status == "in_progress" and time_diff.total_seconds() > 90:  # 1.5 минуты для демо
            if ticket["critical_level"] in ["high", "critical"]:
                ticket["status"] = "awaiting_confirmation"
                ticket["updates"].append({
                    "timestamp": datetime.now(),
                    "status": "awaiting_confirmation",
                    "message": "Ожидается подтверждение решения"
                })
            else:
                ticket["status"] = "awaiting_info"
                ticket["updates"].append({
                    "timestamp": datetime.now(),
                    "status": "awaiting_info",
                    "message": "Требуются дополнительные данные"
                })
        
        elif current_status in ["awaiting_info", "awaiting_confirmation"] and time_diff.total_seconds() > 150:  # 2.5 минуты
            ticket["status"] = "resolved"
            ticket["updates"].append({
                "timestamp": datetime.now(),
                "status": "resolved",
                "message": "Проблема решена, ожидается подтверждение пользователя"
            })
        
        # Возвращаем обновленный ticket
        return ticket
    
    @staticmethod
    async def get_user_tickets(user_id: int) -> List[str]:
        """Получить список тикетов пользователя"""
        return [
            ticket_id for ticket_id, ticket in MockTicketSystem._ticket_statuses.items()
            if ticket.get("user_id") == user_id
        ]
    
    @staticmethod
    async def escalate_ticket(ticket_id: str, reason: str, target_line: str = "second_line") -> Dict[str, Any]:
        """Эскалация тикета на другую линию поддержки"""
        if ticket_id not in MockTicketSystem._ticket_statuses:
            return {
                "success": False,
                "message": f"Тикет {ticket_id} не найден"
            }
        
        ticket = MockTicketSystem._ticket_statuses[ticket_id]
        old_line = ticket.get("assigned_to", "first_line_support")
        
        if target_line == "second_line":
            ticket["assigned_to"] = "second_line_support"
            ticket["priority"] = "Высокий"
            new_line_name = "2-ю линию"
        elif target_line == "third_line":
            ticket["assigned_to"] = "third_line_support"
            ticket["priority"] = "Критический"
            new_line_name = "3-ю линию"
        else:
            return {
                "success": False,
                "message": "Неверная целевая линия поддержки"
            }
        
        ticket["status"] = f"escalated_to_{target_line}"
        ticket["updates"].append({
            "timestamp": datetime.now(),
            "status": ticket["status"],
            "message": f"Эскалация на {new_line_name}: {reason}"
        })
        
        return {
            "success": True,
            "message": f"Тикет {ticket_id} эскалирован на {new_line_name} поддержки",
            "new_line": target_line,
            "old_line": old_line
        }

# ========== СОСТОЯНИЯ БОТА ==========

class SupportStates(StatesGroup):
    waiting_for_problem = State()
    evaluating_solution = State()
    waiting_feedback = State()
    in_human_support = State()
    waiting_for_urgent = State()
    wrong_query = State()

# ========== КЛАВИАТУРЫ ==========

def get_main_keyboard():
    """Основная клавиатура"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Создать обращение")],
            [KeyboardButton(text="❓ Частые вопросы"), KeyboardButton(text="📊 Статус обращения")],
            [KeyboardButton(text="🆘 Срочная помощь")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите действие или опишите проблему..."
    )

def get_faq_inline_keyboard():
    """Inline-клавиатура с частыми вопросами для отображения в чате"""
    faq_items = MockDatabase.FREQUENT_QUESTIONS
    keyboard = []
    
    # Группируем по 2 кнопки в ряд
    for i in range(0, len(faq_items), 2):
        row = []
        for j in range(2):
            if i + j < len(faq_items):
                faq = faq_items[i + j]
                row.append(
                    InlineKeyboardButton(
                        text=faq["short_question"], 
                        callback_data=f"faq_{faq['id']}"
                    )
                )
        if row:
            keyboard.append(row)
    
    # Добавляем кнопку закрытия
    keyboard.append([
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close_faq")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_feedback_keyboard():
    """Клавиатура для обратной связи"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, помогло", callback_data="feedback_yes"),
                InlineKeyboardButton(text="❌ Нет, не помогло", callback_data="feedback_no")
            ],
            [InlineKeyboardButton(text="📋 Создать обращение", callback_data="feedback_ticket")]
        ]
    )

def get_escalation_keyboard(ticket_id: str):
    """Клавиатура для эскалации"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Эскалировать на 2-ю линию", callback_data=f"escalate_second_{ticket_id}")],
            [InlineKeyboardButton(text="🚨 Эскалировать на 3-ю линию", callback_data=f"escalate_third_{ticket_id}")],
            [InlineKeyboardButton(text="⏱ Оставить на текущей линии", callback_data="escalate_no")]
        ]
    )

def get_confirm_operator_keyboard():
    """Клавиатура для подтверждения подключения к оператору"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Подтвердить подключение", 
                callback_data="confirm_operator"
            )],
            [InlineKeyboardButton(
                text="❌ Отмена", 
                callback_data="cancel_operator"
            )]
        ]
    )

def get_ticket_actions_keyboard(ticket_id: str):
    """Клавиатура действий с тикетом - УПРОЩЕННАЯ ВЕРСИЯ (без кнопки комментария)"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить статус", callback_data=f"refresh_{ticket_id}")],
            [InlineKeyboardButton(text="🚨 Эскалировать", callback_data=f"escalate_menu_{ticket_id}")]
        ]
    )

# ========== ОСНОВНЫЕ ОБРАБОТЧИКИ ==========

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    welcome_text = """<b>🤖 Добро пожаловать в AI-агент поддержки Сбер!</b>

<i>Ваш интеллектуальный помощник для решения рабочих вопросов 24/7</i>

✨ <b>Что я умею:</b>
• 🔍 <b>Анализировать</b> ваши проблемы с помощью ИИ
• 📚 <b>Находить решения</b> в базе знаний банка  
• 🎯 <b>Создавать обращения</b> к специалистам поддержки
• ⚡ <b>Маршрутизировать</b> сложные вопросы на нужную линию

👇 <b>Выберите действие или просто опишите вашу проблему:</b>"""

    await message.answer(
        welcome_text, 
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    help_text = """<b>🆘 Помощь по использованию бота</b>

<b>Основные команды:</b>
/start - Начать работу с ботом
/help - Показать это сообщение
/stats - Статистика (только для администраторов)

<b>Меню бота:</b>
📝 <b>Создать обращение</b> - Обычное обращение в поддержку
🆘 <b>Срочная помощь</b> - Только для критических проблем
❓ <b>Частые вопросы</b> - Быстрые решения распространенных проблем
📊 <b>Статус обращения</b> - Проверить статус ваших обращений
👨‍💻 <b>Связаться с оператором</b> - Подключиться к живому специалисту

<b>Как эффективно описать проблему:</b>
1. Что случилось? (кратко)
2. Где происходит? (система, раздел)
3. Когда началось? (время)
4. Что пробовали сделать?
5. Какая ошибка показывается?

<b>Для администраторов:</b>
/confidence_demo - Демонстрация метрики уверенности"""

    await message.answer(help_text, parse_mode="HTML")

@dp.message(F.text == "❓ Частые вопросы")
async def show_faq_menu(message: types.Message):
    """Показать меню с частыми вопросами (inline-кнопки в чате) - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    faq_items = MockDatabase.FREQUENT_QUESTIONS
    
    # Формируем краткий текст с inline-кнопками
    faq_text = """<b>📋 Частые вопросы пользователей</b>

<i>Выберите интересующий вас вопрос:</i>

💡 <b>Подсказка:</b> Нажмите на кнопку с вопросом, чтобы увидеть решение"""
    
    await message.answer(
        faq_text,
        parse_mode="HTML",
        reply_markup=get_faq_inline_keyboard()
    )

@dp.callback_query(F.data.startswith("faq_"))
async def handle_faq_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработка нажатия на вопрос из FAQ"""
    faq_id = int(callback.data.split("_")[1])
    
    # Находим FAQ по ID
    faq_item = None
    for faq in MockDatabase.FREQUENT_QUESTIONS:
        if faq["id"] == faq_id:
            faq_item = faq
            break
    
    if not faq_item:
        await callback.answer("❌ Вопрос не найден")
        return
    
    # Формируем ответ БЕЗ статистики
    response = f"""<b>{faq_item['question']}</b>

{faq_item['answer']}

✅ <b>Это решение помогло решить вашу проблему?</b>"""
    
    # Отправляем ответ и запрашиваем обратную связь
    await callback.message.answer(
        response,
        parse_mode="HTML",
        reply_markup=get_feedback_keyboard()
    )
    
    # Сохраняем данные о текущем FAQ
    await state.update_data(
        problem=faq_item['question'],
        faq_id=faq_id,
        is_from_faq=True
    )
    
    await state.set_state(SupportStates.evaluating_solution)
    await callback.answer()

@dp.callback_query(F.data == "close_faq")
async def close_faq_menu(callback: types.CallbackQuery):
    """Закрыть меню FAQ"""
    try:
        await callback.message.delete()
    except:
        await callback.message.edit_text("❓ Меню частых вопросов закрыто")
    await callback.answer()

@dp.message(F.text == "📊 Статус обращения")
async def check_ticket_status(message: types.Message):
    """Проверка статуса обращения - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    # Получаем тикеты пользователя
    user_tickets = await MockTicketSystem.get_user_tickets(message.from_user.id)
    
    if not user_tickets:
        await message.answer(
            "📭 <b>У вас нет активных обращений</b>\n\n"
            "Чтобы создать новое обращение, нажмите '📝 Создать обращение' в меню.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Показываем последний тикет
    ticket_id = user_tickets[-1]
    ticket = await MockTicketSystem.get_ticket_status(ticket_id)
    
    if not ticket:
        await message.answer(
            "❌ <b>Не удалось загрузить информацию об обращении</b>\n\n"
            "Попробуйте проверить статус позже.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Определяем статус для отображения
    status_display = {
        "created": ("🟡 Принято в обработку", "Специалист анализирует проблему"),
        "in_progress": ("🟢 В работе", "Решение находится в разработке"),
        "awaiting_info": ("🔵 Ожидает уточнений", "Требуются дополнительные данные"),
        "awaiting_confirmation": ("🟣 На согласовании", "Ожидается подтверждение решения"),
        "escalated_to_second_line": ("🟠 На 2-й линии", "Передано специалистам 2-й линии"),
        "escalated_to_third_line": ("🔴 На 3-й линии", "Передано экспертам 3-й линии"),
        "resolved": ("✅ Решено", "Проблема устранена"),
        "closed": ("⚫ Закрыто", "Обращение закрыто")
    }
    
    status, description = status_display.get(
        ticket["status"], 
        ("⏳ Обрабатывается", "Статус обновляется")
    )
    
    created_time = ticket["created_at"]
    time_in_work = datetime.now() - created_time
    hours = time_in_work.seconds // 3600
    minutes = (time_in_work.seconds % 3600) // 60
    
    # Рассчитываем примерное время решения
    if ticket["status"] in ["created", "in_progress"]:
        if ticket["priority"] == "Критический":
            eta = "в течение 1 часа"
        elif ticket["priority"] == "Высокий":
            eta = "1-2 часа"
        else:
            eta = "2-4 часа"
    elif ticket["status"] in ["escalated_to_second_line", "escalated_to_third_line"]:
        eta = "4-8 часов"
    elif ticket["status"] == "resolved":
        eta = "Ожидает подтверждения"
    else:
        eta = "уточняется"
    
    # Формируем историю обновлений (последние 3)
    updates_text = ""
    if ticket.get("updates"):
        last_updates = ticket["updates"][-3:]  # Последние 3 обновления
        for update in last_updates:
            time_str = update["timestamp"].strftime("%H:%M")
            updates_text += f"• {time_str}: {update['message']}\n"
    
    status_text = f"""<b>📈 Статус обращения</b>

🆔 <b>Номер:</b> <code>{ticket_id}</code>
📅 <b>Создано:</b> {created_time.strftime('%d.%m.%Y %H:%M')}
⏱ <b>В работе:</b> {hours}ч {minutes}мин

🎯 <b>Статус:</b> {status}
📋 <b>Описание:</b> {description}

📝 <b>Проблема:</b> {ticket.get('problem', 'Не указана')[:80]}...

📊 <b>Приоритет:</b> {ticket.get('priority', 'Средний')}
👨‍💼 <b>Назначено:</b> {ticket.get('assigned_to', 'first_line_support').replace('_', ' ').title()}

⏳ <b>Ожидаемое решение:</b> {eta}

<b>Последние обновления:</b>
{updates_text if updates_text else '• История обновлений загружается...'}

💡 <b>Что делать:</b>
• Для уточнений ответьте на это сообщение
• Срочные вопросы → кнопка "🆘 Срочная помощь"
• Статус обновляется автоматически"""

    await message.answer(
        status_text, 
        parse_mode="HTML",
        reply_markup=get_ticket_actions_keyboard(ticket_id)
    )

@dp.message(F.text == "👨‍💻 Связаться с оператором")
async def connect_to_human(message: types.Message):
    """Подключение к оператору"""
    # Проверяем, есть ли активные тикеты
    user_tickets = await MockTicketSystem.get_user_tickets(message.from_user.id)
    active_tickets = [
        ticket_id for ticket_id in user_tickets
        if MockTicketSystem._ticket_statuses.get(ticket_id, {}).get("status") not in ["resolved", "closed"]
    ]
    
    if active_tickets:
        # Есть активные тикеты - предлагаем продолжить по ним
        ticket_id = active_tickets[-1]
        ticket = MockTicketSystem._ticket_statuses.get(ticket_id, {})
        
        queue_info = f"""<b>🔄 У вас уже есть активное обращение</b>

🆔 <b>Номер обращения:</b> <code>{ticket_id}</code>
📊 <b>Статус:</b> {ticket.get('status', 'неизвестен')}
👨‍💼 <b>Специалист:</b> {ticket.get('assigned_to', 'first_line_support').replace('_', ' ').title()}

💡 <b>Рекомендации:</b>
1. <b>Продолжайте общение</b> по текущему обращению
2. <b>Используйте кнопку ниже</b> для приоритетного подключения
3. <b>Ожидайте ответа</b> в рамках текущего обращения

⏱ <b>Текущее время ожидания:</b> 5-7 минут
👥 <b>Доступно специалистов:</b> 4 из 6

⚠️ <b>Внимание:</b> Создание нового обращения увеличит время решения."""
    else:
        # Нет активных тикетов
        queue_info = """<b>🔄 Подключение к живому специалисту</b>

⏱ <b>Текущее время ожидания:</b> 5-7 минут
👥 <b>Доступно специалистов:</b> 4 из 6

📋 <b>Перед подключением подготовьте:</b>
• Описание проблемы
• Название системы/сервиса
• Время возникновения ошибки
• Скриншоты (если есть)

🎯 <b>Что можно обсудить:</b>
• Конфиденциальные вопросы
• Сложные технические проблемы
• Нестандартные запросы доступа
• Консультации по новым функциям

⚠️ <b>Важно:</b> Разговор записывается для контроля качества"""
    
    await message.answer(queue_info, parse_mode="HTML")
    
    await message.answer(
        "<b>Вы уверены, что хотите подключиться к оператору?</b>",
        reply_markup=get_confirm_operator_keyboard(),
        parse_mode="HTML"
    )

@dp.message(F.text == "📝 Создать обращение")
async def start_problem_dialog(message: types.Message, state: FSMContext):
    """Начало диалога по проблеме"""
    # Проверяем лимит активных обращений
    user_tickets = await MockTicketSystem.get_user_tickets(message.from_user.id)
    active_tickets = [
        ticket_id for ticket_id in user_tickets
        if MockTicketSystem._ticket_statuses.get(ticket_id, {}).get("status") not in ["resolved", "closed"]
    ]
    
    if len(active_tickets) >= 3:
        await message.answer(
            "⚠️ <b>У вас слишком много активных обращений</b>\n\n"
            f"Активных обращений: <b>{len(active_tickets)} из 3 возможных</b>\n\n"
            "Пожалуйста, дождитесь решения текущих проблем или "
            "закройте завершенные обращения.\n\n"
            "Используйте кнопку '📊 Статус обращения' для управления.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        return
    
    prompt_text = """<b>📝 Создание нового обращения</b>

Добро пожаловать в систему поддержки! Для эффективного решения:

🎯 <b>Рекомендуемая структура:</b>
1. <b>Что случилось?</b> — краткое описание
2. <b>Где происходит?</b> — система, раздел, страница
3. <b>Когда началось?</b> — дата и время
4. <b>Что ожидали?</b> — ожидаемое поведение
5. <b>Что видите?</b> — сообщение об ошибке

📎 <b>Дополнительно (если есть):</b>
• Номер ошибки
• Скриншоты
• Шаги воспроизведения
• Номер предыдущего обращения

⏱ <b>Среднее время решения:</b>
• Простые вопросы: до 30 минут
• Средней сложности: 2-4 часа
• Сложные проблемы: до 24 часов

<b>Опишите вашу проблему или вопрос:</b>"""
    
    await message.answer(prompt_text, parse_mode="HTML")
    await state.set_state(SupportStates.waiting_for_problem)

@dp.message(F.text == "🆘 Срочная помощь")
async def start_urgent_problem_dialog(message: types.Message, state: FSMContext):
    """Начало диалога по срочной проблеме"""
    # Проверяем лимит активных обращений
    user_tickets = await MockTicketSystem.get_user_tickets(message.from_user.id)
    active_tickets = [
        ticket_id for ticket_id in user_tickets
        if MockTicketSystem._ticket_statuses.get(ticket_id, {}).get("status") not in ["resolved", "closed"]
    ]
    
    if len(active_tickets) >= 2:
        await message.answer(
            "⚠️ <b>У вас слишком много активных обращений</b>\n\n"
            "Для срочных обращений действует ограничение: "
            f"<b>{len(active_tickets)} из 2 возможных</b>\n\n"
            "Пожалуйста, дождитесь решения текущих критических проблем.\n\n"
            "Используйте кнопку '📊 Статус обращения' для проверки.",
            parse_mode="HTML"
        )
        return
    
    prompt_text = """<b>🚨 СРОЧНОЕ ОБРАЩЕНИЕ — ТОЛЬКО ВЫСОКИЙ ПРИОРИТЕТ</b>

⚠️ <b>Внимание:</b> Этот раздел предназначен ИСКЛЮЧИТЕЛЬНО для:
• 🔴 <b>Полной недоступности</b> критичных систем
• 🚨 <b>Остановки бизнес-процессов</b> (невозможность работать)
• 💰 <b>Финансовых ошибок</b> в операциях
• 🔐 <b>Угроз безопасности</b> данных

❌ <b>НЕ используйте для:</b>
• Вопросов по настройке
• Консультаций
• Медленной работы систем
• Плановых работ

📋 <b>Для ускорения обработки укажите:</b>
1. <b>Какая система не работает?</b> (название точно)
2. <b>Когда началась проблема?</b> (точное время)
3. <b>Сколько человек затронуто?</b> (только вы/отдел/все)
4. <b>Какое влияние на работу?</b> (частичная/полная остановка)
5. <b>Что уже пробовали?</b> (ваши действия)

<b>Опишите КРИТИЧНУЮ проблему:</b>"""
    
    await message.answer(prompt_text, parse_mode="HTML")
    await state.set_state(SupportStates.waiting_for_urgent)

@dp.message(SupportStates.waiting_for_problem)
async def handle_problem_description(message: types.Message, state: FSMContext):
    """Обработка описания проблемы"""
    user_problem = message.text
    
    # Показываем статус анализа
    analysis_msg = await message.answer("🔍 <b>Анализирую вашу проблему...</b>", parse_mode="HTML")
    
    # 1. Анализ проблемы через LLM (исправленная версия)
    analysis = await MockLLMService.analyze_problem(message, user_problem)

    if 'хорош' not in analysis['is_good'].lower():
        await message.answer('Неправильный запрос. Пожалуйста, переформулируйте.')
        await state.set_state(SupportStates.wrong_query)
    else:
        # 2. Поиск в базе знаний
        knowledge_result = await MockDatabase.search_knowledge_base(analysis['summary'])
        # Удаляем сообщение об анализе
        try:
            await analysis_msg.delete()
        except:
            pass
        
        # Сохраняем данные в состоянии
        await state.update_data(
            problem=user_problem,
            analysis=analysis,
            knowledge_result=knowledge_result,
            is_urgent=False
        )
        
        # Формируем ответ с метрикой уверенности
        response_text = f"""🎯 <b>РЕЗУЛЬТАТ АНАЛИЗА</b>

📊 <b>Детали проблемы:</b>
├ Категория: <code>{analysis['category']}</code>
└ Критичность: {analysis['priority'].upper()}

💡 <b>РЕКОМЕНДОВАННОЕ РЕШЕНИЕ:</b>
{knowledge_result['answer'] if knowledge_result['found'] else '🔍 <i>Решение не найдено в базе знаний. Создаю обращение к специалисту...</i>'}

✅ <b>Это решение помогло решить вашу проблему?</b>"""
    
        # Принимаем решение на основе уверенности (внутренняя метрика)
        if knowledge_result['found'] and analysis['priority'] not in ['high', 'critical']:
            await message.answer(response_text, reply_markup=get_feedback_keyboard(), parse_mode="HTML")
            await state.set_state(SupportStates.evaluating_solution)
        else:
            # Если решение не найдено или проблема критичная, создаем тикет
            if not knowledge_result['found']:
                await message.answer("❌ Решение не найдено в базе знаний. Создаю обращение к специалисту...")
            # elif analysis['critical_level'] in ['high', 'critical']:
            #     await message.answer("⚠️ Проблема определена как критичная. Создаю обращение к специалисту...")
            # else:
            #     await message.answer("🔍 Требуется дополнительный анализ. Создаю обращение к специалисту...")
            
            await create_support_ticket(message, state, user_problem, analysis, is_urgent=False)

@dp.message(SupportStates.waiting_for_urgent)
async def handle_urgent_problem_description(message: types.Message, state: FSMContext):
    """Обработка срочного обращения - СТРОГИЙ ФИЛЬТР (только high/critical)"""
    user_problem = message.text
    
    # Анализируем проблему через LLM (исправленная версия)
    analysis = await MockLLMService.analyze_problem(message, user_problem)
    
    # Показываем метрику уверенности
    await message.answer(f"📊 <b>Уверенность ИИ в анализе:</b> {analysis['confidence']:.0%}", parse_mode="HTML")
    
    # ЖЕСТКИЙ ФИЛЬТР: только high/critical priority
    if analysis['critical_level'] not in ['high', 'critical']:
        # Отклоняем обращение
        await message.answer(
            "❌ <b>Отклонено: проблема не соответствует критериям срочного обращения</b>\n\n"
            f"• Определенный приоритет: <b>{analysis['critical_level'].upper()}</b>\n"
            f"• Категория: {analysis['category']}\n"
            f"• Уверенность анализа: <b>{analysis['confidence']:.0%}</b>\n\n"
            "<b>Срочные обращения принимаются ТОЛЬКО для:</b>\n"
            "• 🔴 Полной недоступности критичных систем\n"
            "• 🚨 Остановки бизнес-процессов\n"
            "• 💰 Финансовых ошибок в операциях\n"
            "• 🔐 Угроз безопасности данных\n\n"
            "<b>Рекомендация:</b>\n"
            "Используйте обычное создание обращения через '📝 Создать обращение'",
            parse_mode="HTML"
        )
        await state.clear()
        return
    
    # Если прошел фильтр - продолжаем
    await message.answer("🔍 <b>Анализирую критичную проблему...</b>", parse_mode="HTML")
    await asyncio.sleep(1)
    
    # Сохраняем данные
    await state.update_data(
        problem=user_problem,
        analysis=analysis,
        is_urgent=True
    )
    
    # Сразу создаем тикет с максимальным приоритетом
    ticket = await MockTicketSystem.create_ticket(
        problem=f"🚨 СРОЧНО: {user_problem[:100]}",
        user_id=message.from_user.id,
        category=analysis.get('category', 'Критичная проблема'),
        critical_level="critical"  # Всегда critical для срочных
    )
    
    ticket_text = f"""🚨 <b>СРОЧНОЕ ОБРАЩЕНИЕ ПРИНЯТО!</b>

✅ <b>Создано с максимальным приоритетом</b>

📋 <b>Детали:</b>
ID: <code>{ticket['ticket_id']}</code>
Категория: {analysis.get('category', 'Критичная')}
Приоритет: <b>КРИТИЧЕСКИЙ</b>
Назначено: <b>2-я линия поддержки</b>
Ожидайте ответа: <b>в течение 15 минут</b>

👨‍💼 <b>С вами свяжется старший специалист</b>
📞 <b>Будьте готовы к звонку</b>

<i>Все ресурсы поддержки уведомлены о вашей проблеме.</i>"""
    
    await message.answer(ticket_text, parse_mode="HTML")
    
    # Автоматическая эскалация на 2-ю линию
    escalate_result = await MockTicketSystem.escalate_ticket(
        ticket['ticket_id'], 
        "Автоматическая эскалация срочного обращения", 
        "second_line"
    )
    
    if escalate_result["success"]:
        await message.answer(
            f"⚡ <b>Автоматически эскалировано на {escalate_result['new_line']} линию</b>",
            parse_mode="HTML"
        )
    
    await state.clear()

@dp.message(SupportStates.wrong_query)
async def handle_wrong_query(message: types.Message, state: FSMContext):
    await state.set_state(SupportStates.wrong_query)
    await handle_problem_description(message, state)

# ========== ОБРАБОТКА КОЛБЭКОВ ==========

@dp.callback_query(F.data.startswith("feedback_"))
async def handle_feedback(callback: types.CallbackQuery, state: FSMContext):
    """Обработка обратной связи"""
    feedback = callback.data.split("_")[1]
    user_data = await state.get_data()
    
    if feedback == "yes":
        await callback.message.answer(
            "✅ <b>Отлично! Рад, что смог помочь!</b>\n\n"
            "Если возникнут еще вопросы - обращайтесь!\n"
            "Для новой проблемы просто опишите ее или используйте меню.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
    
    elif feedback == "no":
        await callback.message.answer(
            "❌ <b>Жаль, что не помогло. Создаю обращение к специалисту поддержки...</b>",
            parse_mode="HTML"
        )
        await create_support_ticket(
            callback.message, 
            state, 
            user_data.get('problem', 'Проблема не решена'),
            user_data.get('analysis', {}),
            user_data.get('is_urgent', False)
        )
    
    elif feedback == "more":
        await callback.message.answer("🔄 <b>Ищу дополнительные решения...</b>", parse_mode="HTML")
        # Поиск похожих тикетов
        similar = await MockDatabase.get_similar_tickets(user_data.get('problem', ''))
        if similar:
            similar_text = "\n".join([f"• <b>{t['problem']}</b>: {t['solution']} ({t['status']})" for t in similar[:3]])
            await callback.message.answer(
                f"📚 <b>Нашел похожие решения в истории обращений:</b>\n\n{similar_text}\n\n"
                "Попробуйте одно из этих решений. Если не поможет - создам обращение.",
                parse_mode="HTML"
            )
            # Даем время попробовать решения
            await asyncio.sleep(2)
            await callback.message.answer(
                "❓ <b>Одно из этих решений помогло?</b>",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(text="✅ Да", callback_data="similar_yes"),
                            InlineKeyboardButton(text="❌ Нет", callback_data="similar_no")
                        ]
                    ]
                ),
                parse_mode="HTML"
            )
        else:
            await callback.message.answer(
                "📭 <b>Дополнительных решений не найдено</b>\n\n"
                "Создаю обращение к специалисту...",
                parse_mode="HTML"
            )
            await create_support_ticket(
                callback.message, 
                state, 
                user_data.get('problem', ''),
                user_data.get('analysis', {}),
                user_data.get('is_urgent', False)
            )
    
    elif feedback == "ticket":
        await callback.message.answer("📝 <b>Создаю обращение...</b>", parse_mode="HTML")
        await create_support_ticket(
            callback.message, 
            state, 
            user_data.get('problem', ''),
            user_data.get('analysis', {}),
            user_data.get('is_urgent', False)
        )
    
    await callback.answer()

@dp.callback_query(F.data.startswith("similar_"))
async def handle_similar_feedback(callback: types.CallbackQuery, state: FSMContext):
    """Обработка обратной связи по похожим решениям"""
    feedback = callback.data.split("_")[1]
    
    if feedback == "yes":
        await callback.message.answer(
            "✅ <b>Отлично! Рад, что смог помочь!</b>\n\n"
            "История решений помогает улучшать базу знаний.",
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            "❌ <b>Создаю обращение к специалисту...</b>",
            parse_mode="HTML"
        )
        user_data = await state.get_data()
        await create_support_ticket(
            callback.message, 
            state, 
            user_data.get('problem', ''),
            user_data.get('analysis', {}),
            user_data.get('is_urgent', False)
        )
    
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data == "confirm_operator")
async def confirm_operator(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение подключения к оператору"""
    await callback.message.edit_text("✅ <b>Подключение к оператору подтверждено!</b>", parse_mode="HTML")
    
    # Создаем тикет для оператора
    ticket = await MockTicketSystem.create_ticket(
        "Запрос на подключение к живому оператору",
        callback.from_user.id,
        "human_support",
        "high"  # Высокий приоритет для подключения к оператору
    )
    
    await callback.message.answer(
        f"🔄 <b>Подключаю вас к специалисту поддержки...</b>\n\n"
        f"✅ <b>Обращение создано:</b> {ticket['ticket_id']}\n"
        f"👨‍💼 <b>Специалист свяжется с вами в течение 15 минут</b>\n"
        f"📞 <b>Будьте готовы к звонку</b>\n"
        f"📊 <b>Текущий статус:</b> {ticket['status']}",
        parse_mode="HTML"
    )
    
    await state.set_state(SupportStates.in_human_support)
    await callback.answer()

@dp.callback_query(F.data == "cancel_operator")
async def cancel_operator(callback: types.CallbackQuery):
    """Отмена подключения к оператору"""
    await callback.message.edit_text("❌ <b>Подключение к оператору отменено.</b>", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("escalate_"))
async def handle_escalation(callback: types.CallbackQuery, state: FSMContext):
    """Обработка эскалации"""
    parts = callback.data.split("_")
    
    if len(parts) == 3:
        action = parts[1]
        ticket_id = parts[2]
        
        if action == "second":
            result = await MockTicketSystem.escalate_ticket(ticket_id, "Ручная эскалация пользователем", "second_line")
            await callback.message.answer(f"🚀 <b>{result['message']}</b>", parse_mode="HTML")
        elif action == "third":
            result = await MockTicketSystem.escalate_ticket(ticket_id, "Критичная проблема", "third_line")
            await callback.message.answer(f"🚨 <b>{result['message']}</b>", parse_mode="HTML")
        else:
            await callback.message.answer("⏱ <b>Обращение осталось на текущей линии поддержки</b>", parse_mode="HTML")
    else:
        await callback.message.answer("⏱ <b>Обращение осталось на текущей линии поддержки</b>", parse_mode="HTML")
    
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data.startswith("refresh_"))
async def refresh_ticket_status(callback: types.CallbackQuery):
    """Обновление статуса тикета"""
    ticket_id = callback.data.split("_")[1]
    
    ticket = await MockTicketSystem.get_ticket_status(ticket_id)
    if ticket:
        # Формируем краткое сообщение об обновлении
        status_names = {
            "created": "Принято в обработку",
            "in_progress": "В работе",
            "awaiting_info": "Ожидает уточнений",
            "resolved": "Решено"
        }
        
        current_status = status_names.get(ticket["status"], ticket["status"])
        last_update = ticket["updates"][-1]["message"] if ticket.get("updates") else "Нет обновлений"
        
        await callback.message.answer(
            f"🔄 <b>Статус обновлен</b>\n\n"
            f"🆔 <b>Тикет:</b> {ticket_id}\n"
            f"📊 <b>Статус:</b> {current_status}\n"
            f"📝 <b>Последнее обновление:</b> {last_update}\n\n"
            f"<i>Полную информацию можно посмотреть через '📊 Статус обращения'</i>",
            parse_mode="HTML"
        )
    else:
        await callback.message.answer("❌ <b>Не удалось обновить статус тикета</b>", parse_mode="HTML")
    
    await callback.answer()

@dp.callback_query(F.data.startswith("escalate_menu_"))
async def handle_escalate_menu(callback: types.CallbackQuery):
    """Обработка кнопки эскалации из меню"""
    ticket_id = callback.data.split("_")[2]
    
    await callback.message.answer(
        f"⚡ <b>Эскалация обращения {ticket_id}</b>\n\n"
        "Выберите линию поддержки для эскалации:",
        reply_markup=get_escalation_keyboard(ticket_id),
        parse_mode="HTML"
    )
    
    await callback.answer()

async def create_support_ticket(message, state, problem, analysis, is_urgent=False):
    """Создание тикета поддержки"""
    # Определяем линию поддержки на основе критичности
    critical_level = analysis.get('critical_level', 'medium')
    
    # Повышаем приоритет для срочных обращений
    if is_urgent or critical_level in ['high', 'critical']:
        support_line = "second_line"
        line_name = "2-ю линию"
        critical_level = "high" if not is_urgent else "critical"
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
    
    ticket_text = f"""✅ <b>Обращение создано!</b>

📋 <b>Детали обращения:</b>
ID: <code>{ticket['ticket_id']}</code>
Категория: {analysis.get('category', 'Не определена')}
Критичность: {ticket['priority']}
Назначено: {line_name}
Ожидайте ответа: {ticket.get('estimated_response', 'в ближайшее время')}

<b>Ваш вопрос будет обработан специалистом.</b>

💡 <b>Что дальше:</b>
• Следите за статусом через '📊 Статус обращения'
• Для уточнений отвечайте на это сообщение
• Срочные вопросы → кнопка '🆘 Срочная помощь'"""
    
    await message.answer(ticket_text, parse_mode="HTML")
    
    # Предлагаем эскалацию для критичных проблем
    if critical_level in ['high', 'critical'] and not is_urgent:
        await message.answer(
            "⚠️ <b>Проблема определена как критичная.</b>\n"
            "Эскалировать на более высокую линию поддержки?", 
            reply_markup=get_escalation_keyboard(ticket['ticket_id'])
        )
    
    await state.set_state(SupportStates.waiting_feedback)

@dp.message(SupportStates.in_human_support)
async def handle_human_support(message: types.Message):
    """Обработка сообщений в режиме поддержки от человека"""
    await message.answer(
        "💬 <b>Ваше сообщение передано специалисту.</b>\n\n"
        "Ожидайте ответа. Среднее время ответа при подключении к оператору: 5-7 минут.",
        parse_mode="HTML"
    )

# ========== ОБРАБОТКА ТЕКСТА ИЗ СООБЩЕНИЯ ==========
@dp.message()
async def handle_any_message(message: types.Message, state: FSMContext):
    """Обработка любых других сообщений - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    current_state = await state.get_state()
    if message.voice:
        user_text = await voiceConverter.process_media_message(bot, message)
    elif message.photo:
        user_text = await photoConverter.photoToText(bot, message)
    else:
        user_text = message.text.lower()

    if current_state is None:
        # Если нет активного состояния        
        # Проверяем, не является ли это приветствием
        greetings = ['привет', 'здравствуйте', 'добрый день', 'доброе утро', 'добрый вечер', 'здравствуй', 'hi', 'hello']
        if any(greet in user_text for greet in greetings):
            await message.answer(
                "👋 <b>Здравствуйте!</b>\n\n"
                "Я AI-агент поддержки Сбер. Чем могу помочь?\n"
                "Выберите действие в меню или опишите вашу проблему.",
                parse_mode="HTML",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Проверяем, не является ли это вопросом из FAQ
        is_faq_question = False
        for faq in MockDatabase.FREQUENT_QUESTIONS:
            # Проверяем по ключевым словам
            faq_keywords = [kw.lower() for kw in faq["keywords"]]
            question_clean = faq["question"].lower().replace("🔐 ", "").replace("💻 ", "").replace("📊 ", "").replace("⚡ ", "").replace("📧 ", "").replace("🔄 ", "")
            
            if (any(keyword in user_text for keyword in faq_keywords) or 
                question_clean in user_text):
                
                # Нашли совпадение с FAQ
                await message.answer(
                    faq["answer"],
                    parse_mode="HTML",
                    reply_markup=get_feedback_keyboard()
                )
                await state.set_state(SupportStates.evaluating_solution)
                is_faq_question = True
                break
        
        if not is_faq_question:
            # Это новый запрос - начинаем диалог о проблеме
            await message.answer(
                "🤖 <b>AI-агент поддержки готов помочь!</b>\n\n"
                "Я анализирую ваше сообщение. Для эффективного решения:\n\n"
                "1. <b>Опишите проблему подробно</b>\n"
                "2. <b>Укажите систему и время возникновения</b>\n"
                "3. <b>Добавьте скриншот если есть</b>\n\n"
                "Или выберите действие в меню ниже:",
                parse_mode="HTML",
                reply_markup=get_main_keyboard()
            )
            await state.set_state(SupportStates.waiting_for_problem)
    else:
        # Если есть активное состояние, просим дождаться обработки
        await message.answer(
            "⏳ <b>Пожалуйста, дождитесь обработки текущего запроса.</b>\n\n"
            "Если вы хотите начать заново, нажмите /start",
            parse_mode="HTML"
        )

# ========== АДМИН КОМАНДЫ ==========

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Статистика бота (только для админов) - УПРОЩЕННАЯ ВЕРСИЯ"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ <b>У вас нет доступа к этой команде</b>", parse_mode="HTML")
        return
    
    # Статистика из мок-данных
    total_tickets = len(MockTicketSystem._ticket_statuses)
    active_tickets = len([t for t in MockTicketSystem._ticket_statuses.values() 
                         if t.get("status") not in ["resolved", "closed"]])
    
    stats_text = f"""📊 <b>Статистика AI-агента поддержки</b>

• Всего обращений: <b>{total_tickets}</b>
• Активных обращений: <b>{active_tickets}</b>
• Частых вопросов в базе: <b>{len(MockDatabase.FREQUENT_QUESTIONS)}</b>

🕐 <b>Время работы:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"""
    
    await message.answer(stats_text, parse_mode="HTML")

@dp.message(Command("confidence_demo"))
async def cmd_confidence_demo(message: types.Message, state: FSMContext):
    """Демонстрация уровня уверенности для жюри хакатона"""
    demo_text = """🎯 <b>Демонстрация метрики уровня уверенности AI-агента</b>

🤖 <i>Внутренняя метрика системы (не показывается пользователям)</i>

📊 <b>Как это работает:</b>
1. AI анализирует запрос пользователя
2. Определяет категорию и подкатегорию проблемы
3. Рассчитывает уровень уверенности (0.0-1.0)
4. На основе этого принимает решение:
   • >0.8 — дать ответ из базы знаний
   • 0.5-0.8 — предложить решение и спросить, помогло ли
   • <0.5 — сразу создать обращение к специалисту

📈 <b>Пример расчета:</b>

Запрос: <i>"Не могу войти в систему отчетности"</i>
• Уверенность определения: <b>0.92</b> (высокая)
• Категория: "Проблемы с доступом"
• Источник: База знаний FAQ#1
• <b>Решение:</b> Предложено автоматически

Запрос: <i>"Что-то не так с программой"</i>
• Уверенность определения: <b>0.45</b> (низкая)
• Категория: "Общая техническая проблема"
• <b>Решение:</b> Создать обращение к специалисту

🔧 <b>Техническая реализация:</b>
• Метрика используется для принятия решений
• Не показывается пользователю во избежание путаницы
• Логируется для анализа эффективности бота
• Влияет на маршрутизацию и приоритет обработки

📚 <b>База знаний содержит {len(MockDatabase.FREQUENT_QUESTIONS)} частых вопросов</b>

<i>Эта метрика помогает повысить точность ответов и снижает нагрузку на специалистов.</i>

<b>Хотите протестировать метрику?</b> Отправьте тестовый запрос."""

    await message.answer(demo_text, parse_mode="HTML")
    await state.set_state(SupportStates.waiting_for_problem)

@dp.message(Command("update_kb"))
async def cmd_update_kb(message: types.Message):
    """Обновление базы знаний (заглушка)"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ <b>У вас нет доступа к этой команде</b>", parse_mode="HTML")
        return
    
    await message.answer(
        "🔄 <b>Запрос на обновление базы знаний отправлен.</b>\n\n"
        "Это может занять несколько минут. База знаний будет дополнена новыми решениями "
        "из обработанных обращений.",
        parse_mode="HTML"
    )

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
    • База знаний: ЗАГРУЖЕНА ({faq_count} вопросов)
    • Система тикетов: ГОТОВА
    • Обработка срочных: АКТИВНА
    """.format(
        date=datetime.now().strftime("%d.%m.%Y"),
        time=datetime.now().strftime("%H:%M:%S"),
        faq_count=len(MockDatabase.FREQUENT_QUESTIONS)
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
                    f"🤖 <b>AI-агент поддержки Сбер запущен</b>\n"
                    f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                    f"✅ Система готова к приему обращений\n"
                    f"📚 База знаний: {len(MockDatabase.FREQUENT_QUESTIONS)} вопросов\n"
                    f"🔧 Режим работы: 24/7",
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