# projects_parser.py
import requests
import json
import logging
import re  # Работа с регулярными выражениями (для "чистки" текста от HTML-мусора)
import html
from source.config import API_URL_TEMPLATE
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

MAX_SLICES = 3

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
KNOWLEDGE_BASE_FILE = DATA_DIR / "knowledge_base.json"


def clean_html(raw_html):
    if not raw_html:
        return ''
    text = re.sub(r'<.*?>', ' ', raw_html)
    text = html.unescape(text)
    return ' '.join(text.split())


def fetch_data_from_slice(slice_number):
    url = API_URL_TEMPLATE.format(slice_num=slice_number)
    logging.info(f"Запрос данных со страницы {slice_number}: {url}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logging.error(f"Таймаут при запросе к API для slice {slice_number}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе к API ({type(e).__name__}) для slice {slice_number}: {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Ошибка декодирования JSON от API для slice {slice_number}: {e}. Ответ: {response.text[:200]}")
        return None


def extract_project_info(product_data):
    """Извлекаем и форматируем информацию о проекте из данных API."""
    title = product_data.get('title', 'Название не указано')
    full_description = clean_html(product_data.get('text', ''))
    short_description = clean_html(product_data.get('descr', ''))
    raw_link = product_data.get('brand', '')
    link_to_project = raw_link if raw_link.startswith(('http://', 'https://')) else ''
    if not title:
        logging.warning("Найден проект без названия. Проверьте данные API.")
    if not short_description and not full_description:
        logging.warning(f"Проект '{title}' не имеет описания.")
    if not link_to_project:
        logging.warning(f"Проект '{title}' имеет невалидную ссылку: '{raw_link}'")
    direction = "Не указано"
    duration = "Не указано"
    characteristics = product_data.get('characteristics', [])
    for char in characteristics:
        char_title = char.get('title')
        char_value = char.get('value')
        if char_title == "Направление":
            direction = char_value
        elif char_title == "Длительность работы":
            duration = char_value
    return {
        "title": title,
        "direction": direction,
        "duration": duration,
        "short_description": short_description,
        "full_description": full_description,
        "link_to_project": link_to_project
    }


def extract_filter_options(api_filters_data):
    """Извлекает доступные опции для фильтров (направления, длительности) с количеством."""
    available_filters = {
        "directions": [],
        "durations": []
    }
    if not api_filters_data:
        logging.warning("Данные для извлечения фильтров отсутствуют.")
        return available_filters
    filters_list = api_filters_data.get("filters", [])
    if not filters_list:
        logging.warning("В данных API отсутствует ключ 'filters' или он пуст.")
        return available_filters
    for filter_item in filters_list:
        label = filter_item.get("label")
        values_with_counts = filter_item.get("values", [])
        processed_values = []
        for val_obj in values_with_counts:
            if val_obj.get("value") is not None and val_obj.get("count") is not None:
                processed_values.append({
                    "value": str(val_obj.get("value")),
                    "count": int(val_obj.get("count"))
                })
            else:
                logging.warning(
                    f"Пропущен элемент фильтра для '{label}' из-за отсутствия 'value' или 'count': {val_obj}")
        if label == "Направление":
            available_filters["directions"] = processed_values
        elif label == "Длительность работы":
            available_filters["durations"] = processed_values
    if not available_filters["directions"] and not available_filters["durations"]:
        logging.warning("Не удалось извлечь ни одного значения для фильтров Направление или Длительность работы.")
    return available_filters


def parse_and_save_data():
    """Основная функция парсера: получает данные, обрабатывает и сохраняет."""
    logging.info("Запуск парсера VK Education Projects...")
    all_projects = []
    parsed_filter_options = {"directions": [], "durations": []}
    got_filters = False
    for i in range(1, MAX_SLICES + 1):
        raw_page_data = fetch_data_from_slice(i)
        if not raw_page_data:
            logging.warning(f"Не удалось получить данные со страницы {i}. Пропускаем.")
            continue
        if raw_page_data.get("status") == "ERROR":
            logging.error(
                f"API Тильды вернуло ошибку для страницы {i}: {raw_page_data.get('message', 'Нет сообщения об ошибке')}")
            continue
        if not got_filters and "filters" in raw_page_data:
            parsed_filter_options = extract_filter_options(raw_page_data.get("filters"))
            if parsed_filter_options["directions"] or parsed_filter_options["durations"]:
                logging.info(
                    f"Извлечены опции для фильтров: Направления - {len(parsed_filter_options['directions'])}, Длительности - {len(parsed_filter_options['durations'])}")
                got_filters = True
        products_on_page = raw_page_data.get('products', [])
        if not products_on_page:
            logging.info(f"На странице {i} не найдено проектов (поле 'products' пустое или отсутствует).")
            total_api = raw_page_data.get('total')
            if total_api is not None and len(all_projects) >= total_api:
                logging.info(f"Собрано {len(all_projects)} проектов, что соответствует total={total_api}. Завершаем сбор проектов.")
                break
            continue
        logging.info(f"Обработка {len(products_on_page)} проектов со страницы {i}...")
        for product_data in products_on_page:
            project_info = extract_project_info(product_data)
            if any(p["title"] == project_info["title"] for p in all_projects):
                continue
            all_projects.append(project_info)
        logging.info(f"Страница {i} обработана. Всего собрано проектов: {len(all_projects)}")
    if raw_page_data and raw_page_data.get('total') is not None:
        api_total_projects = raw_page_data.get('total')
        if len(all_projects) != api_total_projects:
            logging.warning(
                f"Собрано {len(all_projects)} проектов, но API сообщает о {api_total_projects} всего. Возможно, MAX_SLICES ({MAX_SLICES}) неверно или есть проблемы с API.")
    elif not all_projects:
        logging.error("Не удалось собрать ни одного проекта. Проверьте URL API и доступность сайта.")
        return
    knowledge_base_content = {
        "available_projects": all_projects,
        "available_filters": parsed_filter_options
    }
    try:
        with open(KNOWLEDGE_BASE_FILE, 'w', encoding='utf-8') as f:
            json.dump(knowledge_base_content, f, ensure_ascii=False, indent=4)
        logging.info(f"Данные успешно сохранены в {KNOWLEDGE_BASE_FILE}. Всего проектов: {len(all_projects)}.")
    except IOError as e:
        logging.error(f"Ошибка записи в файл {KNOWLEDGE_BASE_FILE}: {e}")


if __name__ == '__main__':
    parse_and_save_data()