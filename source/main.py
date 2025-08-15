# main.py
import json                               # Работа с JSON-строкой payload-а
import logging                            # Логирование событий
import time                               # Пауза между переподключениями

import vk_api                             # Основная библиотека для VK API
from vk_api.bot_longpoll import (         # Модуль LongPoll для сообществ
    VkBotLongPoll,
    VkBotEventType,
)
from vk_api.utils import get_random_id    # Генерация random_id для сообщений
from vk_api.exceptions import ApiError    # Исключения VK API

from source.config import TOKEN, GROUP_ID        # Токен сообщества и его ID
from source.bot_logic import generate_keyboard_response      # Бизнес-логика ответа
from source.bot_data import ERROR_FALLBACK_MESSAGE           # Запасной ответ при ошибке

# ------------------------------------------------------------------------------
# Функция автоматического обновления данных в базе (ПОКА ОТКЛЮЧЕНА)
# ------------------------------------------------------------------------------

# from apscheduler.schedulers.background import BackgroundScheduler
# from source.projects_parser import parse_and_save_data
# sched = BackgroundScheduler()
# sched.add_job(parse_and_save_data, "interval", hours=12)
# sched.start()
# parse_and_save_data()

# ------------------------------------------------------------------------------
# Настраиваем логирование: вывод в консоль с датой и уровнем
# ------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,                   # Уровень логирования (DEBUG/INFO/…)
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)      # Логгер для текущего модуля

# ------------------------------------------------------------------------------
# Основной цикл работы бота
# ------------------------------------------------------------------------------


def run_bot() -> None:
    logger.info("Запускаем бота VK Education…")               # Стартовое сообщение
    logger.info("Успешное подключение к VK API")              # Подтверждаем коннект
    while True:                                               # Цикл перезапуска при ошибках
        try:
            vk_session = vk_api.VkApi(token=TOKEN)  # Создаём VK-сессию
            vk = vk_session.get_api()  # Высокоуровневый доступ
            longpoll = VkBotLongPoll(vk_session, group_id=GROUP_ID)  # Инициализируем longpoll
            logger.info("LongPoll запущен заново")

            for event in longpoll.listen():                   # Слушаем события VK
                if event.type != VkBotEventType.MESSAGE_NEW:  # Нас интересуют только новые сообщения
                    continue
                if not event.from_user:                       # Игнорируем сообщения из чатов/ботов
                    continue

                msg = event.message                           # Объект сообщения
                user_id = msg.from_id                         # ID пользователя
                raw_text = (msg.text or "").strip()           # Текст сообщения

                payload = None                                # Значение payload по умолчанию
                if msg.payload:                               # Если payload присутствует
                    try:
                        payload = json.loads(msg.payload)     # Пытаемся распарсить payload как JSON
                    except json.JSONDecodeError:
                        logger.warning(                       # Логируем ошибку парсинга payload
                            f"Не удалось распарсить payload: {msg.payload}"
                        )

                # ----------------------- ЛОГ — входящее сообщение -----------------------
                logger.info(
                    f"Пользователь {user_id} прислал: '{raw_text}' | payload={payload}"
                )

                if not raw_text and not payload:              # Если сообщение пустое и без payload
                    continue                                   # Пропускаем

                # ----------------------- ВЫЗОВ БИЗНЕС-ЛОГИКИ ---------------------------
                try:
                    response_text, keyboard_json = generate_keyboard_response(
                        user_id=user_id,
                        text=raw_text,
                        payload=payload,
                    )
                except Exception as e:                        # Ловим ошибки логики
                    logger.exception(                         # Пишем стек-трейс
                        "Ошибка в generate_keyboard_response: %s", e
                    )
                    response_text, keyboard_json = ERROR_FALLBACK_MESSAGE, None

                if not response_text:                         # Если ответ пустой — ничего не шлём
                    continue

                params = {                                    # Параметры метода messages.send
                    "peer_id": user_id,                       # Адресат
                    "message": response_text,                 # Текст ответа
                    "random_id": get_random_id(),             # Случайный ID для уникальности
                }

                if keyboard_json:                             # При наличии клавиатуры
                    params["keyboard"] = keyboard_json        # Добавляем её в параметры

                try:
                    vk.messages.send(**params)                # Отправляем сообщение
                    # ----------- ЛОГ — исходящее сообщение (успешно отправлено) ----------
                    logger.info(
                        f"Бот ответил пользователю {user_id}: '{response_text[:60]}'"
                    )
                except ApiError as e:                         # Ошибка VK API
                    logger.error("VK ApiError при отправке: %s", e)
        except Exception as e:                                # Любая критическая ошибка цикла
            logger.error(                                     # Логируем и ждём 5 сек
                "LongPoll error: %s, перезапуск через 5 сек…", e
            )
            time.sleep(5)                                     # Пауза перед повтором

# ------------------------------------------------------------------------------
# Точка входа
# ------------------------------------------------------------------------------


if __name__ == "__main__":
    try:
        run_bot()                                             # Запускаем бота
    except KeyboardInterrupt:                                 # Корректная остановка Ctrl+C
        logger.info("Бот остановлен по Ctrl+C")
# a

