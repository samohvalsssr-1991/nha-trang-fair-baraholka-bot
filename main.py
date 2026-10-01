import os
import re
import json
import time
import urllib.request
import urllib.parse


# ============================================================
# НАСТРОЙКИ
# ============================================================

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

GROUP_ID = "-1001776236864"
GROUP_THREAD_ID = 17186

ADMIN_IDS = {
    int(x.strip())
    for x in os.environ.get("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

API_URL = f"https://api.telegram.org/bot{TOKEN}/"


# ============================================================
# ДАННЫЕ
# ============================================================

user_states = {}
user_posts = {}
flood_data = {}


# ============================================================
# TELEGRAM API
# ============================================================

def api(method, data=None):
    if not TOKEN:
        return None

    if data is None:
        data = {}

    encoded = urllib.parse.urlencode(data).encode("utf-8")

    try:
        req = urllib.request.Request(
            API_URL + method,
            data=encoded,
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    except Exception as e:
        print("API ERROR:", method, e)
        return None


def send_message(chat_id, text, reply_markup=None, message_thread_id=None):
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }

    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)

    if message_thread_id is not None:
        data["message_thread_id"] = message_thread_id

    return api("sendMessage", data)


def edit_message(chat_id, message_id, text, reply_markup=None):
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }

    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)

    return api("editMessageText", data)


def delete_message(chat_id, message_id):
    return api(
        "deleteMessage",
        {
            "chat_id": chat_id,
            "message_id": message_id
        }
    )


def pin_message(chat_id, message_id):
    return api(
        "pinChatMessage",
        {
            "chat_id": chat_id,
            "message_id": message_id,
            "disable_notification": "true"
        }
    )


def ban_user(chat_id, user_id):
    return api(
        "banChatMember",
        {
            "chat_id": chat_id,
            "user_id": user_id
        }
    )


def answer_callback(callback_id):
    return api(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id
        }
    )


def get_me():
    return api("getMe")


# ============================================================
# АДМИНЫ
# ============================================================

def is_admin(user_id):
    return user_id in ADMIN_IDS


def is_chat_admin(chat_id, user_id):
    result = api(
        "getChatMember",
        {
            "chat_id": chat_id,
            "user_id": user_id
        }
    )

    if not result or not result.get("ok"):
        return False

    status = result["result"].get("status")

    return status in (
        "administrator",
        "creator"
    )


# ============================================================
# КЛАВИАТУРЫ
# ============================================================

def main_menu():
    return {
        "keyboard": [
            [{"text": "📢 Подать объявление"}],
            [{"text": "📋 Правила"}, {"text": "❓ Помощь"}]
        ],
        "resize_keyboard": True
    }


def moderation_keyboard(post_id):
    return {
        "inline_keyboard": [
            [
                {
                    "text": "✅ Опубликовать",
                    "callback_data": f"approve:{post_id}"
                },
                {
                    "text": "❌ Отклонить",
                    "callback_data": f"reject:{post_id}"
                }
            ],
            [
                {
                    "text": "🚫 Заблокировать",
                    "callback_data": f"ban:{post_id}"
                }
            ]
        ]
    }


def submission_keyboard():
    return {
        "inline_keyboard": [
            [
                {
                    "text": "📢 Подать объявление",
                    "url": "https://t.me/NhaTrangFairBaraholkaBot?start=newpost"
                }
            ]
        ]
    }


def baraholka_button():
    return {
        "inline_keyboard": [
            [
                {
                    "text": "📢 Подать объявление",
                    "url": "https://t.me/NhaTrangFairBaraholkaBot?start=newpost"
                }
            ]
        ]
    }


# ============================================================
# СИЛЬНЫЙ ФИЛЬТР
# ============================================================

def normalize(text):
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[\u200b\u200c\u200d]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def forbidden_reason(text):
    text = normalize(text)

    # Убираем пробелы/дефисы для проверки скрытых ссылок
    compact = re.sub(r"[\s\-_]+", "", text)

    # --------------------------------------------------------
    # АРЕНДА ЖИЛЬЯ
    # --------------------------------------------------------

    rental_words = (
        r"(?:сда(?:ю|ем|ет|ется|еться)|сдается|сдам|"
        r"снять|сниму|снимаю|аренд\w*|"
        r"посуточн\w*|помесячн\w*|долгосрочн\w*|"
        r"на\s+(?:день|сутки|недел\w*|месяц)|"
        r"rent|rental|for\s+rent|renting|"
        r"cho\s*thu[eê]|thu[eê])"
    )

    housing_words = (
        r"(?:квартир\w*|апартамент\w*|студи\w*|"
        r"комнат\w*|дом\w*|вилл\w*|жиль\w*|кондо|"
        r"condo|apartment|studio|room|house|villa)"
    )

    if re.search(
        rf"{rental_words}.{{0,100}}{housing_words}",
        text,
        re.I
    ):
        return "аренда квартир/домов"

    if re.search(
        rf"{housing_words}.{{0,100}}{rental_words}",
        text,
        re.I
    ):
        return "аренда квартир/домов"

    if re.search(
        r"\bcho\s*thu[eê]\b.{0,100}"
        r"\b(?:căn|can|hộ|ho|nhà|phòng|studio|villa)\b",
        text,
        re.I
    ):
        return "аренда квартир/домов"

    if re.search(
        r"\b(?:căn\s*hộ|can\s*ho|nhà|phòng|studio|villa)\b"
        r".{0,100}\b(?:cho\s*thu[eê]|thu[eê])\b",
        text,
        re.I
    ):
        return "аренда квартир/домов"

    # Отдельно ловим популярные варианты:
    if re.search(
        r"\b(?:сдается|сдается|сдам|сдаю)\b.{0,100}"
        r"\b(?:студи\w*|квартир\w*|апартамент\w*|комнат\w*|дом\w*|вилл\w*)\b",
        text,
        re.I
    ):
        return "аренда квартир/домов"

    if re.search(
        r"\b(?:студи\w*|квартир\w*|апартамент\w*|комнат\w*|дом\w*|вилл\w*)\b"
        r".{0,100}\b(?:сдается|сдам|сдаю)\b",
        text,
        re.I
    ):
        return "аренда квартир/домов"

    # --------------------------------------------------------
    # АРЕНДА МОТОБАЙКОВ
    # --------------------------------------------------------

    bike_rental = (
        r"(?:аренд\w*|сдам|сдается|сдаю|прокат\w*|"
        r"rent|rental|for\s+rent|renting|"
        r"на\s+(?:день|сутки|недел\w*|месяц)|"
        r"посуточн\w*|помесячн\w*|"
        r"cho\s*thu[eê]|thu[eê])"
    )

    bike_words = (
        r"(?:байк\w*|мотобайк\w*|мотоцикл\w*|"
        r"мото\w*|скутер\w*|мопед\w*|"
        r"bike|motorbike|motor\s*bike|scooter|"
        r"xe\s*m[aá]y|xe|"
        r"pcx|airblade|vario|vision|lead|nvx|adv|xmax)"
    )

    if re.search(
        rf"{bike_rental}.{{0,80}}{bike_words}",
        text,
        re.I
    ):
        return "аренда мотобайков"

    if re.search(
        rf"{bike_words}.{{0,80}}{bike_rental}",
        text,
        re.I
    ):
        return "аренда мотобайков"

    if re.search(
        r"\bcho\s*thu[eê]\s+(?:xe\s*m[aá]y|xe)\b",
        text,
        re.I
    ):
        return "аренда мотобайков"

    if re.search(
        r"\b(?:xe\s*m[aá]y|xe)\s+cho\s*thu[eê]\b",
        text,
        re.I
    ):
        return "аренда мотобайков"

    if re.search(
        r"\b(?:bike|motorbike|motor\s*bike|scooter)"
        r"\s+(?:rental|for\s+rent)\b",
        text,
        re.I
    ):
        return "аренда мотобайков"

    if re.search(
        r"\b(?:rent|rental)\s+(?:a\s+)?"
        r"(?:bike|motorbike|scooter)\b",
        text,
        re.I
    ):
        return "аренда мотобайков"

    # --------------------------------------------------------
    # ОБМЕН ВАЛЮТ
    # --------------------------------------------------------

    exchange_words = (
        r"(?:обмен\w*|обменя\w*|меняю|поменя\w*|"
        r"currency\s+exchange|money\s+exchange|exchange|"
        r"đổi\s+tiền|doi\s+tien|"
        r"đổi\s+ngoại\s+tệ|doi\s+ngoai\s+te|"
        r"mua\s+b[aá]n\s+ngo[aạ]i\s+t[eê])"
    )

    currency_words = (
        r"(?:валют\w*|деньг\w*|рубл\w*|доллар\w*|"
        r"донг\w*|евро\w*|usdt|usd|rub|vnd|eur|"
        r"rmb|юан\w*|тенге\w*|currency|money|"
        r"foreign\s+currency|ngoại\s+tệ|ngoai\s+te)"
    )

    if re.search(
        rf"{exchange_words}.{{0,80}}{currency_words}",
        text,
        re.I
    ):
        return "обмен валют"

    if re.search(
        rf"{currency_words}.{{0,80}}{exchange_words}",
        text,
        re.I
    ):
        return "обмен валют"

    if re.search(
        r"(?:рубл\w*|доллар\w*|евро\w*|донг\w*|usd|rub|vnd|eur)"
        r".{0,40}(?:на|в|по)\s+"
        r"(?:рубл\w*|доллар\w*|евро\w*|донг\w*|usd|rub|vnd|eur)",
        text,
        re.I
    ):
        return "обмен валют"

    if re.search(
        r"(?:usd|rub|vnd|eur|usdt|rmb)"
        r"\s*[/\-]\s*"
        r"(?:usd|rub|vnd|eur|usdt|rmb)",
        text,
        re.I
    ) and re.search(
        r"(?:обмен|курс|меняю|поменя|куплю|"
        r"продам|exchange|rate|обменять)",
        text,
        re.I
    ):
        return "обмен валют"

    # --------------------------------------------------------
    # КАЗИНО / СТАВКИ
    # --------------------------------------------------------

    if re
