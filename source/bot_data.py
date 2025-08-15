# bot_data.py
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # корень проекта
BAD_WORDS_FILE_PATH = BASE_DIR / "data" / "Bad_Words_List.txt"
BAD_WORDS = {
    w.strip().lower()
    for w in BAD_WORDS_FILE_PATH.read_text(encoding="utf-8").splitlines()
    if w.strip()
}

_WORD_RE = re.compile(r"[А-Яа-яЁёA-Za-z\-]+")


def contains_bad_words(text: str) -> bool:
    """
    True, если в тексте встречается слово из BAD_WORDS.
    Работает O(n) по количеству токенов.
    """
    tokens = (w.lower() for w in _WORD_RE.findall(text))
    return any(tok in BAD_WORDS for tok in tokens)


VK_EDUCATION_URL = "https://education.vk.company/"
VK_EDUCATION_ALL_PROJECTS_URL = "https://education.vk.company/education_projects/"

#  Текстовые сообщения
WELCOME_MESSAGE_AFTER_START = (
            "Привет! Я бот VK Education Projects.\n"
            "Помогу подобрать учебный проект, отвечу на частые вопросы "
            "и покажу контактную информацию.\n"
            "Выбирайте действие кнопками ниже 👇"
        )

DEFAULT_FALLBACK_MESSAGE = ("Я не нашёл ответа 🤔. Попробуйте переформулировать вопрос или воспользуйтесь кнопками "
                            "меню.")

ERROR_FALLBACK_MESSAGE = "Ой, что-то пошло не так на моей стороне. Попробуй написать 'Начать' или 'Старт' "

CONTACTS_TEXT = (
            "Если возникли трудности:\n"
            "• Пишите на info@education.vk.company\n"
            "• Или задайте вопрос в сообществе VK Education - vk.com/vkeducation\n\n"
            "• Сайт VK Education:\n https://education.vk.company/\n"
            "• Сайт VK Education Projects:\n https://education.vk.company/education_projects/\n"
        )

BAD_WORDS_WARNING = "Пожалуйста, без ненормативной лексики 🙂"


# BOT_ABILITIES_MESSAGE = "Сообщение, описывающее, что умеет бот"
# PROJECT_OPTIONS_MESSAGE = " Сообщение перед выбором опций поиска проекта"
# CHOOSE_DIRECTION_MESSAGE = " Сообщение перед выбором направления"
# CHOOSE_DURATION_MESSAGE = "Сообщение перед выбором длительности"
# NO_DIRECTIONS_FOUND_MESSAGE = "Сообщение, если направления не найдены"
# NO_DURATIONS_FOUND_MESSAGE = "Сообщение, если длительности не найдены"
# PROJECTS_FOR_DIRECTION_MESSAGE = "Сообщение перед показом проектов по направлению"
# PROJECTS_FOR_DURATION_MESSAGE = "Сообщение перед показом проектов по длительности"
# SHOW_ALL_PROJECTS_MESSAGE = "Сообщение перед показом всех проектов"
# FAQ_CATEGORIES_MESSAGE = "Сообщение перед выбором категории FAQ"
# NO_PROJECTS_FOUND_MESSAGE = "Сообщение, если проектов по запросу не найдено"
