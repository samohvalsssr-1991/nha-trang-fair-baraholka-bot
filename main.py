import os
import re
import json
import time
import html
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
        print("ERROR: TELEGRAM_BOT_TOKEN is not set")
        return None

    if data is None:
        data = {}

    encoded = urllib.parse.urlencode(data).encode("utf-8")

    try:
        request = urllib.request.Request(
            API_URL + method,
            data=encoded,
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    except Exception as e:
        print(f"API ERROR [{method}]: {e}")
        return None


def send_message(chat_id, text, reply_markup=None, message_thread_id=None):
    data = {
        "chat_id": chat_id,
        "text": text,
    }

    if reply_markup:
        data["reply_markup"] = json.dumps(
            reply_markup,
            ensure_ascii=False
        )

    if message_thread_id is not None:
        data["message_thread_id"] = message_thread_id

    return api("sendMessage", data)


def send_html_message(chat_id, text, reply_markup=None, message_thread_id=None):
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }

    if reply_markup:
        data["reply_markup"] = json.dumps(
            reply_markup,
            ensure_ascii=False
        )

    if message_thread_id is not None:
        data["message_thread_id"] = message_thread_id

    return api("sendMessage", data)


def edit_message(chat_id, message_id, text, reply_markup=None):
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
    }

    if reply_markup:
        data["reply_markup"] = json.dumps(
            reply_markup,
            ensure_ascii=False
        )

    return api("editMessageText", data)


def delete_message(chat_id, message_id):
    return api(
        "deleteMessage",
        {
            "chat_id": chat_id,
            "message_id": message_id,
        }
    )


def pin_message(chat_id, message_id):
    return api(
        "pinChatMessage",
        {
            "chat_id": chat_id,
            "message_id": message_id,
            "disable_notification": "true",
        }
    )


def ban_user(chat_id, user_id):
    return api(
        "banChatMember",
        {
            "chat_id": chat_id,
            "user_id": user_id,
        }
    )


def answer_callback(callback_id, text=None):
    data = {
        "callback_query_id": callback_id,
    }

    if text:
        data["text"] = text

    return api("answerCallbackQuery", data)


def get_me():
    return api("getMe")


def get_chat(chat_id):
    return api(
        "getChat",
        {
            "chat_id": chat_id,
        }
    )


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
            "user_id": user_id,
        }
    )

    if not result or not result.get("ok"):
        return False

    status = result["result"].get("status")

    return status in ("administrator", "creator")


# ============================================================
# КЛАВИАТУРЫ
# ============================================================

def main_menu():
    return {
        "keyboard": [
            [{"text": "📢 Подать объявление"}],
            [{"text": "📋 Правила"}, {"text": "❓ Помощь"}],
        ],
        "resize_keyboard": True,
    }


def moderation_keyboard(post_id):
    return {
        "inline_keyboard": [
            [
                {
                    "text": "✅ Опубликовать",
                    "callback_data": f"approve:{post_id}",
                },
                {
                    "text": "❌ Отклонить",
                    "callback_data": f"reject:{post_id}",
                },
            ],
            [
                {
                    "text": "🚫 Заблокировать",
                    "callback_data": f"ban:{post_id}",
                },
            ],
        ]
    }


def baraholka_button():
    return {
        "inline_keyboard": [
            [
                {
                    "text": "📢 Подать объявление",
                    "url": "https://t.me/NhaTrangFairBaraholkaBot?start=newpost",
                }
            ]
        ]
    }


# ============================================================
# ФИЛЬТР
# ============================================================

def normalize(text):
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[\u200b\u200c\u200d]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def forbidden_reason(text):
    text = normalize(text)
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
        re.I,
    ):
        return "аренда квартир/домов"

    if re.search(
        rf"{housing_words}.{{0,100}}{rental_words}",
        text,
        re.I,
    ):
        return "аренда квартир/домов"

    if re.search(
        r"\bcho\s*thu[eê]\b.{0,100}"
        r"\b(?:căn|can|hộ|ho|nhà|phòng|studio|villa)\b",
        text,
        re.I,
    ):
        return "аренда квартир/домов"

    if re.search(
        r"\b(?:căn\s*hộ|can\s*ho|nhà|phòng|studio|villa)\b"
        r".{0,100}\b(?:cho\s*thu[eê]|thu[eê])\b",
        text,
        re.I,
    ):
        return "аренда квартир/домов"

    # Популярные варианты без расстояния между словами
    if re.search(
        r"\b(?:сдается|сдам|сдаю)\b.{0,100}"
        r"\b(?:студи\w*|квартир\w*|апартамент\w*|"
        r"комнат\w*|дом\w*|вилл\w*)\b",
        text,
        re.I,
    ):
        return "аренда квартир/домов"

    if re.search(
        r"\b(?:студи\w*|квартир\w*|апартамент\w*|"
        r"комнат\w*|дом\w*|вилл\w*)\b.{0,100}"
        r"\b(?:сдается|сдам|сдаю)\b",
        text,
        re.I,
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
        r"xe\s*m[aá]y|xe|pcx|airblade|vario|"
        r"vision|lead|nvx|adv|xmax)"
    )

    if re.search(
        rf"{bike_rental}.{{0,80}}{bike_words}",
        text,
        re.I,
    ):
        return "аренда мотобайков"

    if re.search(
        rf"{bike_words}.{{0,80}}{bike_rental}",
        text,
        re.I,
    ):
        return "аренда мотобайков"

    if re.search(
        r"\bcho\s*thu[eê]\s+(?:xe\s*m[aá]y|xe)\b",
        text,
        re.I,
    ):
        return "аренда мотобайков"

    if re.search(
        r"\b(?:xe\s*m[aá]y|xe)\s+cho\s*thu[eê]\b",
        text,
        re.I,
    ):
        return "аренда мотобайков"

    if re.search(
        r"\b(?:bike|motorbike|motor\s*bike|scooter)"
        r"\s+(?:rental|for\s+rent)\b",
        text,
        re.I,
    ):
        return "аренда мотобайков"

    if re.search(
        r"\b(?:rent|rental)\s+(?:a\s+)?"
        r"(?:bike|motorbike|scooter)\b",
        text,
        re.I,
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
        re.I,
    ):
        return "обмен валют"

    if re.search(
        rf"{currency_words}.{{0,80}}{exchange_words}",
        text,
        re.I,
    ):
        return "обмен валют"

    if re.search(
        r"(?:рубл\w*|доллар\w*|евро\w*|донг\w*|usd|rub|vnd|eur)"
        r".{0,40}(?:на|в|по)\s+"
        r"(?:рубл\w*|доллар\w*|евро\w*|донг\w*|usd|rub|vnd|eur)",
        text,
        re.I,
    ):
        return "обмен валют"

    if re.search(
        r"(?:usd|rub|vnd|eur|usdt|rmb)"
        r"\s*[/\-]\s*"
        r"(?:usd|rub|vnd|eur|usdt|rmb)",
        text,
        re.I,
    ) and re.search(
        r"(?:обмен|курс|меняю|поменя|куплю|продам|"
        r"exchange|rate|обменять)",
        text,
        re.I,
    ):
        return "обмен валют"

    # --------------------------------------------------------
    # КАЗИНО / СТАВКИ
    # --------------------------------------------------------

    if re.search(
        r"\b(?:казино|casino|ставк\w*|betting|"
        r"sportsbook|1xbet|pin\s*up|pinup|bet|"
        r"букмекер\w*)\b",
        text,
        re.I,
    ):
        return "казино/ставки"

    # --------------------------------------------------------
    # КРИПТОРЕКЛАМА
    # --------------------------------------------------------

    crypto = (
        r"(?:крипт\w*|crypto|usdt|bitcoin|btc|"
        r"ethereum|eth|binance|bybit)"
    )

    crypto_promo = (
        r"(?:заработ\w*|инвест\w*|доход\w*|"
        r"прибыл\w*|profit|income|invest\w*|"
        r"сигнал\w*|гарант\w*|пассивн\w*|"
        r"трейдинг|trading)"
    )

    if re.search(
        rf"{crypto}.{{0,80}}{crypto_promo}",
        text,
        re.I,
    ):
        return "криптореклама"

    if re.search(
        rf"{crypto_promo}.{{0,80}}{crypto}",
        text,
        re.I,
    ):
        return "криптореклама"

    # --------------------------------------------------------
    # ССЫЛКИ
    # --------------------------------------------------------

    link_pattern = (
        r"(?:https?://|www\.|"
        r"t\.me/|telegram\.me/|telegram\.dog/|"
        r"wa\.me/|chat\.whatsapp\.com/|"
        r"discord\.gg/|vk\.com/)"
    )

    if re.search(link_pattern, text, re.I):
        return "ссылка"

    if re.search(link_pattern, compact, re.I):
        return "ссылка"

    # Скрытые ссылки: t . me /..., telegram . me /..., wa . me /...
    if re.search(r"\bt\s*\.\s*me\s*/", text, re.I):
        return "ссылка"

    if re.search(r"\btelegram\s*\.\s*me\s*/", text, re.I):
        return "ссылка"

    if re.search(r"\bwa\s*\.\s*me\s*/", text, re.I):
        return "ссылка"

    # --------------------------------------------------------
    # РЕКЛАМА СВОИХ ГРУПП / КАНАЛОВ
    # --------------------------------------------------------

    group_promo = [
        r"\bнаша\s+групп\w*",
        r"\bнаши\s+групп\w*",
        r"\bнаш\s+канал\w*",
        r"\bнаши\s+канал\w*",
        r"\bвступайте\s+в\s+(?:нашу\s+|наши\s+)?"
        r"(?:групп\w*|канал\w*)",
        r"\bвступить\s+в\s+(?:нашу\s+|наши\s+)?"
        r"(?:групп\w*|канал\w*)",
        r"\bподписывайтесь\s+на\s+(?:канал\w*|групп\w*)",
        r"\bподпишитесь\s+на\s+(?:канал\w*|групп\w*)",
        r"\bтелеграм\s+(?:канал|группа|группу|чат)\b",
        r"\btelegram\s+(?:channel|group|chat)\b",
        r"\bjoin\s+(?:our\s+)?(?:group|channel|chat)\b",
        r"\bнаш\s+(?:telegram|телеграм)\b",
        r"\bссылка\s+на\s+(?:групп\w*|канал\w*|телеграм)\b",
        r"\bзаходите\s+в\s+(?:нашу\s+|наш\s+)?"
        r"(?:групп\w*|канал\w*|чат\w*)",
        r"\bпереходите\s+в\s+(?:нашу\s+|наш\s+)?"
        r"(?:групп\w*|канал\w*|чат\w*)",
    ]

    for pattern in group_promo:
        if re.search(pattern, text, re.I):
            return "реклама групп/каналов"

    # --------------------------------------------------------
    # ОБЩАЯ РЕКЛАМА
    # --------------------------------------------------------

    if re.search(
        r"\b(?:реклама|рекламн\w*|advertising|"
        r"advertisement|promo|promotion)\b",
        text,
        re.I,
    ):
        return "реклама"

    return None


# ============================================================
# FLOOD
# ============================================================

def flood_check(user_id):
    now = time.time()

    history = flood_data.setdefault(user_id, [])

    history[:] = [
        timestamp
        for timestamp in history
        if now - timestamp < 60
    ]

    if len(history) >= 5:
        return False

    history.append(now)
    return True


# ============================================================
# СОЗДАНИЕ ОБЪЯВЛЕНИЯ
# ============================================================

def create_post(user_id):
    user_posts[user_id] = {
        "text": "",
        "photos": [],
        "price": "",
        "contact": "",
        "created": time.time(),
    }


# ============================================================
# ПРЕДПРОСМОТР
# ============================================================

def build_preview(post):
    text = html.escape(post.get("text", ""))
    price = html.escape(post.get("price", ""))
    contact = html.escape(post.get("contact", ""))

    preview = (
        "👀 <b>Предпросмотр</b>\n\n"
        f"{text}\n\n"
        f"💰 Цена: {price}\n"
        f"📞 Контакт: {contact}"
    )

    photos = post.get("photos", [])

    if photos:
        preview += f"\n\n📷 Фото: {len(photos)}"

    return preview


# ============================================================
# ПУБЛИКАЦИЯ
# ============================================================

def publish_post(post_id):
    post = user_posts.get(post_id)

    if not post:
        return None

    text = html.escape(post.get("text", ""))

    price = html.escape(
        post.get("price", "")
    )

    contact = html.escape(
        post.get("contact", "")
    )

    caption = (
        f"{text}\n\n"
        f"💰 Цена: {price}\n"
        f"📞 Контакт: {contact}"
    )

    photos = post.get("photos", [])

    if photos:
        result = api(
            "sendPhoto",
            {
                "chat_id": GROUP_ID,
                "message_thread_id": GROUP_THREAD_ID,
                "photo": photos[0],
                "caption": caption,
                "parse_mode": "HTML",
                "reply_markup": json.dumps(
                    baraholka_button(),
                    ensure_ascii=False,
                ),
            },
        )

        # Если есть дополнительные фото — отправляем их отдельными сообщениями
        if result and result.get("ok") and len(photos) > 1:
            for photo_id in photos[1:]:
                api(
                    "sendPhoto",
                    {
                        "chat_id": GROUP_ID,
                        "message_thread_id": GROUP_THREAD_ID,
                        "photo": photo_id,
                    },
                )

        return result

    return send_html_message(
        GROUP_ID,
        caption,
        baraholka_button(),
        GROUP_THREAD_ID,
    )


# ============================================================
# МОДЕРАЦИЯ
# ============================================================

def send_moderation(user_id):
    post = user_posts.get(user_id)

    if not post:
        return False

    text = html.escape(
        post.get("text", "")
    )

    price = html.escape(
        post.get("price", "")
    )

    contact = html.escape(
        post.get("contact", "")
    )

    moderation_text = (
        "📢 <b>Новое объявление</b>\n\n"
        f"{text}\n\n"
        f"💰 Цена: {price}\n"
        f"📞 Контакт: {contact}"
    )

    photos = post.get("photos", [])

    if photos:
        moderation_text += f"\n\n📷 Фото: {len(photos)}"

    success = False

    for admin_id in ADMIN_IDS:
        result = send_html_message(
            admin_id,
            moderation_text,
            moderation_keyboard(user_id),
        )

        if result and result.get("ok"):
            success = True

    return success


# ============================================================
# КНОПКА В ТЕМЕ БАРАХОЛКА
# ============================================================

def ensure_baraholka_button():
    # Проверяем, что бот имеет доступ к группе.
    chat = get_chat(GROUP_ID)

    if not chat or not chat.get("ok"):
        print("ERROR: бот не может получить доступ к группе")
        return

    pinned = chat["result"].get("pinned_message")

    button_text = (
        "📢 <b>Подать объявление в барахолку</b>\n\n"
        "Нажмите кнопку ниже и отправьте объявление через бота.\n"
        "Все объявления проходят модерацию."
    )

    # Если наша кнопка уже закреплена — просто обновляем её.
    # Это не создаёт дубликаты после каждого перезапуска Railway.
    if pinned:
        pinned_chat_id = str(
            pinned.get("chat", {}).get("id", "")
        )

        pinned_thread_id = pinned.get("message_thread_id")

        if (
            pinned_chat_id == GROUP_ID
            and pinned_thread_id == GROUP_THREAD_ID
        ):
            result = edit_message(
                GROUP_ID,
                pinned["message_id"],
                button_text,
                baraholka_button(),
            )

            if result and result.get("ok"):
                print("Кнопка барахолки уже закреплена и обновлена")
                return

    # Если закреплённого сообщения нет или его нельзя обновить —
    # создаём новое в теме Барахолка и закрепляем.
    result = send_html_message(
        GROUP_ID,
        button_text,
        baraholka_button(),
        GROUP_THREAD_ID,
    )

    if result and result.get("ok"):
        message_id = result["result"]["message_id"]

        pin_result = pin_message(
            GROUP_ID,
            message_id,
        )

        if pin_result and pin_result.get("ok"):
            print("Кнопка барахолки опубликована и закреплена")
        else:
            print("Кнопка опубликована, но закрепить её не удалось")
    else:
        print("ERROR: не удалось создать кнопку в теме Барахолка")


# ============================================================
# PRIVATE MESSAGE
# ============================================================

def handle_private_message(message):
    user = message.get("from", {})
    user_id = user.get("id")

    text = message.get("text", "").strip()

    if not user_id:
        return

    # --------------------------------------------------------
    # START
    # --------------------------------------------------------

    if text.startswith("/start"):
        parts = text.split(maxsplit=1)

        if len(parts) > 1 and parts[1] == "newpost":
            create_post(user_id)

            user_states[user_id] = {
                "step": "text"
            }

            send_message(
                user_id,
                "📢 Подача объявления\n\n"
                "Напишите текст объявления.\n\n"
                "После этого бот попросит добавить фото, цену и контакт.",
                main_menu(),
            )

            return

        send_message(
            user_id,
            "🏠 Nha Trang Fair Барахолка\n\n"
            "Здесь можно подать объявление о продаже, покупке "
            "или отдаче вещей.",
            main_menu(),
        )

        return

    # --------------------------------------------------------
    # ПОДАТЬ ОБЪЯВЛЕНИЕ
    # --------------------------------------------------------

    if text == "📢 Подать объявление":
        create_post(user_id)

        user_states[user_id] = {
            "step": "text"
        }

        send_message(
            user_id,
            "📝 Напишите текст объявления:",
            main_menu(),
        )

        return

    # --------------------------------------------------------
    # ПРАВИЛА
    # --------------------------------------------------------

    if text == "📋 Правила":
        send_message(
            user_id,
            "📋 Правила барахолки\n\n"
            "Разрешены объявления о продаже, покупке и отдаче вещей.\n\n"
            "🚫 Запрещены:\n"
            "• аренда квартир и домов\n"
            "• аренда мотобайков\n"
            "• обмен валют\n"
            "• казино и ставки\n"
            "• криптореклама\n"
            "• реклама групп и каналов\n"
            "• ссылки\n"
            "• флуд и спам\n\n"
            "Все объявления проходят модерацию.",
        )

        return

    # --------------------------------------------------------
    # ПОМОЩЬ
    # --------------------------------------------------------

    if text == "❓ Помощь":
        send_message(
            user_id,
            "❓ Помощь\n\n"
            "Чтобы разместить объявление, нажмите:\n"
            "📢 Подать объявление\n\n"
            "После отправки оно попадёт на модерацию.",
        )

        return

    state = user_states.get(user_id)

    if not state:
        send_message(
            user_id,
            "Выберите действие в меню:",
            main_menu(),
        )
        return

    # --------------------------------------------------------
    # ТЕКСТ
    # --------------------------------------------------------

    if state["step"] == "text":

        reason = forbidden_reason(text)

        if reason and not is_admin(user_id):
            send_message(
                user_id,
                "🚫 Объявление не принято.\n\n"
                f"Причина: {reason}\n\n"
                "Барахолка предназначена только для объявлений "
                "о продаже, покупке или отдаче вещей.",
            )

            user_states.pop(user_id, None)
            user_posts.pop(user_id, None)

            return

        user_posts[user_id]["text"] = text

        state["step"] = "photos"

        send_message(
            user_id,
            "📷 Отправьте фото объявления.\n\n"
            "Если фото нет — напишите «нет».",
            main_menu(),
        )

        return

    # --------------------------------------------------------
    # ФОТО
    # --------------------------------------------------------

    if state["step"] == "photos":

        if text.lower() in (
            "нет",
            "нет фото",
            "без фото",
            "пропустить",
        ):
            state["step"] = "price"

            send_message(
                user_id,
                "💰 Укажите цену.\n\n"
                "Если цены нет — напишите «нет».",
            )

            return

        if text.lower() in (
            "готово",
            "готов",
            "готова",
        ):
            state["step"] = "price"

            send_message(
                user_id,
                "💰 Укажите цену.\n\n"
                "Если цены нет — напишите «нет».",
            )

            return

        send_message(
            user_id,
            "📷 Пожалуйста, отправьте фото или напишите «нет».",
        )

        return

    # --------------------------------------------------------
    # ЕЩЁ ФОТО
    # --------------------------------------------------------

    if state["step"] == "photos_more":

        if text.lower() in (
            "готово",
            "готов",
            "готова",
            "далее",
            "дальше",
        ):
            state["step"] = "price"

            send_message(
                user_id,
                "💰 Укажите цену.\n\n"
                "Если цены нет — напишите «нет».",
            )

            return

        if text.lower() in (
            "нет",
            "нет фото",
        ):
            state["step"] = "price"

            send_message(
                user_id,
                "💰 Укажите цену.\n\n"
                "Если цены нет — напишите «нет».",
            )

            return

        send_message(
            user_id,
            "📷 Отправьте ещё фото или напишите «готово».",
        )

        return

    # --------------------------------------------------------
    # ЦЕНА
    # --------------------------------------------------------

    if state["step"] == "price":

        if text.lower() in (
            "нет",
            "без цены",
            "договорная",
        ):
            user_posts[user_id]["price"] = "Договорная"
        else:
            reason = forbidden_reason(text)

            if reason and not is_admin(user_id):
                send_message(
                    user_id,
                    "🚫 Это значение не принято.\n\n"
                    f"Причина: {reason}"
                )
                return

            user_posts[user_id]["price"] = text

        state["step"] = "contact"

        send_message(
            user_id,
            "📞 Укажите контакт для связи.\n\n"
            "Например: Telegram username или номер телефона.\n\n"
            "Если хотите не указывать контакт — напишите «нет».",
        )

        return

    # --------------------------------------------------------
    # КОНТАКТ
    # --------------------------------------------------------

    if state["step"] == "contact":

        if text.lower() == "нет":
            user_posts[user_id]["contact"] = "В личные сообщения"
        else:
            reason = forbidden_reason(text)

            if reason and not is_admin(user_id):
                send_message(
                    user_id,
                    "🚫 Этот контакт не принят.\n\n"
                    f"Причина: {reason}"
                )
                return

            user_posts[user_id]["contact"] = text

        state["step"] = "preview"

        post = user_posts[user_id]

        send_html_message(
            user_id,
            build_preview(post) +
            "\n\nОтправить объявление на модерацию?",
            {
                "inline_keyboard": [
                    [
                        {
                            "text": "✅ Отправить",
                            "callback_data": f"submit:{user_id}",
                        }
                    ],
                    [
                        {
                            "text": "❌ Отменить",
                            "callback_data": f"cancel:{user_id}",
                        }
                    ],
                ]
            },
        )

        return


# ============================================================
# PRIVATE PHOTO
# ============================================================

def handle_private_photo(message):
    user = message.get("from", {})
    user_id = user.get("id")

    if not user_id:
        return

    state = user_states.get(user_id)

    if not state:
        return

    if state["step"] not in (
        "photos",
        "photos_more",
    ):
        return

    photos = message.get("photo", [])

    if not photos:
        return

    photo = photos[-1]

    user_posts.setdefault(user_id, {
        "text": "",
        "photos": [],
        "price": "",
        "contact": "",
        "created": time.time(),
    })

    user_posts[user_id].setdefault("photos", [])
    user_posts[user_id]["photos"].append(
        photo["file_id"]
    )

    state["step"] = "photos_more"

    count = len(
        user_posts[user_id]["photos"]
    )

    send_message(
        user_id,
        f"✅ Фото добавлено. Всего фото: {count}\n\n"
        "Можете отправить ещё фото или написать «готово».",
    )


# ============================================================
# CALLBACK
# ============================================================

def handle_callback(callback):
    callback_id = callback.get("id")
    data = callback.get("data", "")
    from_user = callback.get("from", {})
    user_id = from_user.get("id")

    answer_callback(callback_id)

    # --------------------------------------------------------
    # ОТПРАВИТЬ НА МОДЕРАЦИЮ
    # --------------------------------------------------------

    if data.startswith("submit:"):

        target_id = int(data.split(":", 1)[1])

        if target_id != user_id:
            return

        post = user_posts.get(user_id)

        if not post:
            send_message(
                user_id,
                "❌ Объявление не найдено.",
            )
            return

        reason = forbidden_reason(
            post.get("text", "")
        )

        if reason and not is_admin(user_id):
            send_message(
                user_id,
                "🚫 Объявление отклонено.\n\n"
                f"Причина: {reason}",
            )

            user_states.pop(user_id, None)
            user_posts.pop(user_id, None)

            return

        if send_moderation(user_id):
            user_states.pop(user_id, None)

            send_message(
                user_id,
                "✅ Объявление отправлено на модерацию.\n\n"
                "После проверки модератором оно будет опубликовано.",
            )
        else:
            send_message(
                user_id,
                "❌ Не удалось отправить объявление модератору.\n\n"
                "Попробуйте ещё раз позже.",
            )

        return

    # --------------------------------------------------------
    # ОТМЕНА
    # --------------------------------------------------------

    if data.startswith("cancel:"):

        target_id = int(data.split(":", 1)[1])

        if target_id != user_id:
            return

        user_states.pop(user_id, None)
        user_posts.pop(user_id, None)

        send_message(
            user_id,
            "❌ Подача объявления отменена.",
            main_menu(),
        )

        return

    # --------------------------------------------------------
    # ДАЛЬШЕ НУЖЕН АДМИН
    # --------------------------------------------------------

    if not is_admin(user_id):
        return

    # --------------------------------------------------------
    # APPROVE
    # --------------------------------------------------------

    if data.startswith("approve:"):

        post_id = int(data.split(":", 1)[1])

        post = user_posts.get(post_id)

        if not post:
            send_message(
                user_id,
                "❌ Объявление уже обработано.",
            )
            return

        result = publish_post(post_id)

        if result and result.get("ok"):

            send_message(
                post_id,
                "✅ Ваше объявление опубликовано в барахолке.",
            )

            send_message(
                user_id,
                f"✅ Объявление {post_id} опубликовано.",
            )

            user_posts.pop(post_id, None)

        else:
            send_message(
                user_id,
                "❌ Не удалось опубликовать объявление.",
            )

        return

    # --------------------------------------------------------
    # REJECT
    # --------------------------------------------------------

    if data.startswith("reject:"):

        post_id = int(data.split(":", 1)[1])

        post = user_posts.get(post_id)

        if not post:
            send_message(
                user_id,
                "❌ Объявление уже обработано.",
            )
            return

        send_message(
            post_id,
            "❌ Ваше объявление отклонено модератором.",
        )

        user_posts.pop(post_id, None)

        send_message(
            user_id,
            f"❌ Объявление {post_id} отклонено.",
        )

        return

    # --------------------------------------------------------
    # BAN
    # --------------------------------------------------------

    if data.startswith("ban:"):

        post_id = int(data.split(":", 1)[1])

        post = user_posts.get(post_id)

        if not post:
            send_message(
                user_id,
                "❌ Объявление уже обработано.",
            )
            return

        result = ban_user(
            chat_id=GROUP_ID,
            user_id=post_id,
        )

        if result and result.get("ok"):
            send_message(
                user_id,
                f"🚫 Пользователь {post_id} заблокирован в группе.",
            )
        else:
            send_message(
                user_id,
                "❌ Не удалось заблокировать пользователя.",
            )

        user_posts.pop(post_id, None)

        return


# ============================================================
# GROUP MESSAGE
# ============================================================

def handle_group_message(message):
    chat = message.get("chat", {})
    chat_id = str(chat.get("id"))

    if chat_id != GROUP_ID:
        return

    user = message.get("from", {})
    user_id = user.get("id")

    if not user_id:
        return

    # Администраторов не фильтруем
    if is_admin(user_id):
        return

    if is_chat_admin(GROUP_ID, user_id):
        return

    text = message.get("text", "")

    if not text:
        return

    # Проверка запрещённого контента
    reason = forbidden_reason(text)

    if reason:
        message_id = message.get("message_id")

        delete_message(
            GROUP_ID,
            message_id,
        )

        print(
            f"Удалено сообщение {message_id}: {reason}"
        )

        return

    # FLOOD
    if not flood_check(user_id):
        message_id = message.get("message_id")

        delete_message(
            GROUP_ID,
            message_id,
        )

        print(
            f"Удалён flood от пользователя {user_id}"
        )


# ============================================================
# UPDATE
# ============================================================

def process_update(update):

    if "callback_query" in update:
        handle_callback(
            update["callback_query"]
        )
        return

    message = update.get("message")

    if not message:
        return

    chat = message.get("chat", {})
    chat_type = chat.get("type")

    if chat_type == "private":

        if "photo" in message:
            handle_private_photo(message)

        elif "text" in message:
            handle_private_message(message)

        return

    if chat_type in (
        "group",
        "supergroup",
    ):
        handle_group_message(message)


# ============================================================
# MAIN
# ============================================================

def main():

    print("====================================")
    print("Nha Trang Fair Барахолка Bot")
    print("====================================")

    if not TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN отсутствует")
        return

    me = get_me()

    if me and me.get("ok"):
        bot = me["result"]

        print(
            "Bot:",
            bot.get("first_name"),
            "@",
            bot.get("username"),
        )

    else:
        print("ERROR: не удалось подключиться к Telegram API")
        return

    print("GROUP_ID:", GROUP_ID)
    print("GROUP_THREAD_ID:", GROUP_THREAD_ID)
    print("ADMIN_IDS:", ADMIN_IDS)

    # Создаём кнопку в теме Барахолка
    ensure_baraholka_button()

    offset = 0

    while True:

        try:

            result = api(
                "getUpdates",
                {
                    "offset": offset,
                    "timeout": 30,
                    "allowed_updates": json.dumps(
                        [
                            "message",
                            "callback_query",
                        ]
                    ),
                },
            )

            if not result or not result.get("ok"):
                time.sleep(3)
                continue

            updates = result.get("result", [])

            for update in updates:

                offset = update["update_id"] + 1

                try:
                    process_update(update)

                except Exception as e:
                    print(
                        "UPDATE ERROR:",
                        repr(e),
                    )

        except Exception as e:

            print(
                "MAIN LOOP ERROR:",
                repr(e),
            )

            time.sleep(5)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
