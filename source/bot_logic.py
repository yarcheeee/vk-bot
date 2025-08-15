# bot_logic.py - Мозг - разбирает сообщения / payload и формирует (text, keyboard)
# ---------------------------------------------------------------------
import json
import re
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any

from source.keyboards import (  # готовые фабрики клавиатур
    kb_main_menu,
    kb_find_menu,
    kb_faq_page,
    kb_directions_menu,
    kb_durations_menu,
    kb_projects_page,
    make_btn,
    SECONDARY,
    NEGATIVE
)

from source.bot_data import (
    DEFAULT_FALLBACK_MESSAGE,
    CONTACTS_TEXT,
    BAD_WORDS_WARNING,
    contains_bad_words,
    WELCOME_MESSAGE_AFTER_START
)

# 1. Загрузка данных (проекты + FAQ)
# ---------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent        # source/
DATA_DIR = ROOT.parent / "data"               # …/Data

KB_PATH = DATA_DIR / "knowledge_base.json"
FAQ_PATH = DATA_DIR / "faq.json"

with KB_PATH.open(encoding="utf-8") as f:
    KB_RAW = json.load(f)

PROJECTS: List[Dict[str, Any]] = KB_RAW["available_projects"]
FILTERS = KB_RAW["available_filters"]
DIRECTIONS = FILTERS["directions"]
DURATIONS = FILTERS["durations"]

PAGE_SIZE = 5  # сколько проектов на одну страницу

with FAQ_PATH.open(encoding="utf-8") as f:
    _faq_list = json.load(f)["available_answered_questions"]

FAQ_LIST: List[dict] = _faq_list  # упорядоченный список
FAQ_BY_ID: Dict[int, str] = {i: item["answer"] for i, item in enumerate(FAQ_LIST)}

# ---------------------------------------------------------------------
# 2. Утилиты
# ---------------------------------------------------------------------


def normalize(text: str) -> str:
    """Приводим строку к нижнему регистру и убираем лишние символы"""
    text = text.lower()
    text = re.sub(r"[^\w\sа-яё\-]", " ", text)  # всё, кроме букв/цифр/дефиса → пробел
    return re.sub(r"\s{2,}", " ", text).strip()


# def match_faq(text: str) -> Optional[str]:
#     """Ищем точное вхождение вопроса из FAQ"""
#     lt = normalize(text)
#     for q, answer in FAQ_BY_ID.items():
#         if q in lt:
#             return answer
#     return None


# ---------------------------------------------------------------------
# 3. Работа с проектами
# ---------------------------------------------------------------------


def list_projects_short(items: List[Dict[str, Any]], page: int) -> str:
    """
    Возвращает компактный текст-список проектов, которые попали
    на запрошенную страницу пагинации.
    """
    page_items = paginate(items, page)
    if not page_items:
        return "По этому фильтру пока ничего не нашлось."
    start_idx = page * PAGE_SIZE + 1
    lines = [
        f"{idx}. {p['title']} — {p['short_description']} \n"
        for idx, p in enumerate(page_items, start=start_idx)
    ]
    return "\n".join(lines)


def filter_projects(direction: str | None = None,
                    duration: str | None = None) -> List[Dict[str, Any]]:
    """Фильтрация по направлению и/или длительности"""
    res = PROJECTS
    if direction:
        res = [p for p in res if p["direction"] == direction]
    if duration:
        res = [p for p in res if p["duration"] == duration]
    return res


def paginate(items: List[Any], page: int) -> List[Any]:
    start = page * PAGE_SIZE
    return items[start:start + PAGE_SIZE]


def format_project_card(p: Dict[str, Any]) -> str:
    return (
        f"{p['title']}\n"
        f"Направление: {p['direction']}\n"
        f"Длительность: {p['duration']}\n\n"
        f"{p['short_description']}\n\n"
        f"{p['full_description']}\n"
        f"Подробнее: {p['link_to_project']}"
    )


# ---------------------------------------------------------------------
# 4. Главная точка: generate_keyboard_response
# ---------------------------------------------------------------------

def generate_keyboard_response(
        user_id: int,
        text: str,
        payload: Optional[dict] = None
) -> Tuple[str, Optional[str]]:
    """
    На вход – user_id, чистый text, payload (dict или None).
    На выход – (text_answer, keyboard_json_or_None)
    """

    # --------------------------------------------------------------
    # 0. Если прилетел payload (= пользователь нажал кнопку)
    # --------------------------------------------------------------
    if payload and isinstance(payload, dict) and payload.get("cmd"):
        return _handle_command(payload)

    # --------------------------------------------------------------
    # 1. Приветственные триггеры
    # --------------------------------------------------------------
    greet_triggers = {"привет", "здравствуй", "начать", "/start", "hi", "yfxfnm", "старт", "ghbdtn"}
    if normalize(text) in greet_triggers:
        return WELCOME_MESSAGE_AFTER_START, kb_main_menu()

    # --------------------------------------------------------------
    # 2. Проверка на мат
    # --------------------------------------------------------------

    if contains_bad_words(text):
        return BAD_WORDS_WARNING, None

    # --------------------------------------------------------------
    # 3. FAQ-поиск
    # --------------------------------------------------------------
    # faq_ans = match_faq(text)
    # if faq_ans:
    #     return faq_ans, None

    # --------------------------------------------------------------
    # 4. Простой поиск по проектам по ключевым словам
    # --------------------------------------------------------------

    words = normalize(text).split()
    if words:
        hits = [p for p in PROJECTS if any(w in p["title"].lower() for w in words)]
        if hits:
            first = hits[0]
            return format_project_card(first), None

    # --------------------------------------------------------------
    # 5. Фолбэк
    # --------------------------------------------------------------
    return DEFAULT_FALLBACK_MESSAGE, kb_main_menu()


# ---------------------------------------------------------------------
# 5. Обработка payload-команд
# ---------------------------------------------------------------------


def _handle_command(pl: dict) -> Tuple[str, Optional[str]]:
    cmd = pl["cmd"]
    depth = int(pl.get("depth", 0))
    data = pl.get("data") or {}

    # Главное меню
    if cmd in {"go_home"}:
        return "Вы в главном меню. Выберите действие:", kb_main_menu()

    # Шаг назад: bot_logic определит предыдущую клавиатуру по depth-1
    if cmd in {"go_back"}:
        # depth уже уменьшен на 1 в кнопке
        direction = data.get("direction")
        duration = data.get("duration")
        page = int(data.get("page", 0))

        # корень
        if depth <= 0:
            return "Вы в главном меню. Выберите действие:", kb_main_menu()

        # depth==1 → меню «Как будем искать проекты?»
        if depth == 1:
            return "Как будем искать проекты?", kb_find_menu(depth=1)

        # depth==2  → мы были в меню выбора направления/длительности
        if depth == 2:
            if direction:
                return "Выберите направление:", kb_directions_menu(DIRECTIONS, depth=2)
            if duration:
                return "Выберите длительность:", kb_durations_menu(DURATIONS, depth=2)
            # вернулись из «Все проекты»
            return "Как будем искать проекты?", kb_find_menu(depth=1)

        # depth≥3  → вернуться к списку проектов с теми же фильтрами и страницей
        subset = filter_projects(direction, duration)
        listing = list_projects_short(subset, page)
        msg = f"Список проектов (стр. {page + 1}):\n{listing}"
        return msg, kb_projects_page(subset, page, PAGE_SIZE, depth=depth,
                                     extra_filter={k: v for k, v in data.items()
                                                   if k in {"direction", "duration"}})

    # --- уровень 0 → 1 ---
    if cmd == "menu_find":
        return "Как будем искать проекты?", kb_find_menu(depth=1)

    if cmd == "menu_faq":
        intro = "Выберите вопрос, кликнув по нему 👇"
        return intro, kb_faq_page(FAQ_LIST, page=0, page_size=PAGE_SIZE, depth=1)

    if cmd == "faq_page":
        page = int(data.get("page", 0))
        intro = "Выберите вопрос, кликнув по нему 👇"
        return intro, kb_faq_page(FAQ_LIST, page=page, page_size=PAGE_SIZE, depth=1)

    if cmd == "menu_help":
        return CONTACTS_TEXT, kb_main_menu()

    # --- уровень 1 → 2 ---
    if cmd == "find_all_projects":
        page = int(data.get("page", 0))
        listing = list_projects_short(PROJECTS, page)
        text = f"Список всех проектов (страница {page + 1}):\n{listing}"
        return text, kb_projects_page(PROJECTS, page, PAGE_SIZE, depth=3, extra_filter={})  # depth=3 иначе
        # "назад" не работает, костыль

    if cmd == "find_by_direction":
        return "Выберите направление:", kb_directions_menu(DIRECTIONS, depth=2)

    if cmd == "find_by_duration":
        return "Выберите длительность:", kb_durations_menu(DURATIONS, depth=2)

    # --- фильтры направления / длительности ---
    if cmd == "direction_selected":
        direction = data.get("value")
        page = int(data.get("page", 0))
        subset = filter_projects(direction=direction)
        listing = list_projects_short(subset, page)
        msg = f"Проекты по направлению «{direction}» (стр. {page + 1}):\n{listing}"
        return msg, kb_projects_page(subset, page, PAGE_SIZE, depth=3,
                                     extra_filter={"direction": direction})

    if cmd == "duration_selected":
        duration = data.get("value")
        page = int(data.get("page", 0))
        subset = filter_projects(duration=duration)
        listing = list_projects_short(subset, page)
        msg = f"Проекты длительностью «{duration}» (стр. {page + 1}):\n{listing}"
        return msg, kb_projects_page(subset, page, PAGE_SIZE, depth=3,
                                     extra_filter={"duration": duration})

    # --- пагинация ---
    if cmd == "projects_page":
        page = int(data.get("page", 0))
        direction = data.get("direction")
        duration = data.get("duration")
        subset = filter_projects(direction, duration)
        listing = list_projects_short(subset, page)
        text = f"Список проектов (стр. {page + 1}):\n{listing}"
        return text, kb_projects_page(subset, page, PAGE_SIZE, depth=3,
                                      extra_filter={"direction": direction,
                                                    "duration": duration})

    # --- карточка проекта ---
    if cmd == "project_details":
        title = data.get("title")
        page = int(data.get("page", 0))
        direction = data.get("direction")
        duration = data.get("duration")
        proj = next((p for p in PROJECTS if p["title"] == title), None)

        if proj is None:
            return "Проект не найден 🤷‍♂️", kb_main_menu()

        msg = (
            f"Проект - {proj['title']}\n\n"
            f"Направление: {proj['direction']}\n"
            f"Длительность: {proj['duration']}\n\n"
            f"{proj['full_description']}\n\n"
            f"Ссылка: {proj['link_to_project']}"
        )

        # --------- кнопки «Назад» + «Главное меню» -------------
        ctx = {
            "page": page,
            **({"direction": direction} if direction else {}),
            **({"duration": duration} if duration else {})
        }

        tail = [
            make_btn(
                "Назад",
                cmd="go_back",
                depth=depth,  # остаёмся на той же глубине, чтобы вернуть к списку проектов!
                color=NEGATIVE,
                data=ctx  # весь контекст для восстановления списка
            ),
            make_btn(
                "🏠 Главное меню",
                cmd="go_home",
                depth=0,
                color=SECONDARY
            )
        ]

        kb = json.dumps({"buttons": [tail], "one_time": False}, ensure_ascii=False)
        return msg, kb

    if cmd == "faq_answer":
        idx = int(data.get("id", -1))
        answer = FAQ_BY_ID.get(idx, DEFAULT_FALLBACK_MESSAGE)
        question = FAQ_LIST[idx]["question"]
        msg = f"{question}\n\n{answer}"
        return msg, None  # клавиатура остаётся прежней

    # неизвестная команда
    return DEFAULT_FALLBACK_MESSAGE, kb_main_menu()
