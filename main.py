import os
import re
import json
import time
import urllib.request
import urllib.parse

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

GROUP_ID = "-1001776236864"
GROUP_THREAD_ID = 17186

ADMIN_IDS = {
    int(x.strip())
    for x in os.environ.get("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

API_URL = f"https://api.telegram.org/bot{TOKEN}/"

user_states = {}
user_posts = {}
flood_data = {}


def api(method, data=None):
    if not TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set")
        return None

    if data is None:
        data = {}

    try:
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        request = urllib.request.Request(
            API_URL + method,
            data=encoded,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
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

    if reply_markup is not None:
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

    if reply_markup is not None:
        data["reply_markup"] = json.dumps(
            reply_markup,
            ensure_ascii=False
        )

    return api("editMessageText", data)


def send_photo(
    chat_id,
    photo,
    caption=None,
    reply_markup=None,
    message_thread_id=None
):
    data = {
        "chat_id": chat_id,
        "photo": photo,
    }

    if caption:
        data["caption"] = caption

    if reply_markup is not None:
        data["reply_markup"] = json.dumps(
            reply_markup,
            ensure_ascii=False
        )

    if message_thread_id is not None:
        data["message_thread_id"] = message_thread_id

    return api("sendPhoto", data)


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


def get_chat_member(chat_id, user_id):
    return api(
        "getChatMember",
        {
            "chat_id": chat_id,
            "user_id": user_id,
        }
    )


def is_admin(user_id):
    return user_id in ADMIN_IDS


def is_chat_admin(chat_id, user_id):
    result = get_chat_member(chat_id, user_id)

    if not result or not result.get("ok"):
        return False

    status = result["result"].get("status")

    return status in ("administrator", "creator")


def main_menu():
    return {
        "keyboard": [
            [{"text": "📢 Подать объявление"}],
            [
                {"text": "📋 Правила"},
                {"text": "❓ Помощь"}
            ],
        ],
        "resize_keyboard": True,
    }


def text_step_keyboard():
    return {
        "keyboard": [
            [{"text": "❌ Отменить"}],
        ],
        "resize_keyboard": True,
    }


def photo_step_keyboard():
    return {
        "keyboard": [
            [{"text": "➡️ Без фото"}],
            [{"text": "❌ Отменить"}],
        ],
        "resize_keyboard": True,
    }


def photo_more_keyboard():
    return {
        "keyboard": [
            [{"text": "➡️ Готово"}],
            [{"text": "❌ Отменить"}],
        ],
        "resize_keyboard": True,
    }


def price_step_keyboard():
    return {
        "keyboard": [
            [{"text": "➡️ Цена договорная"}],
            [{"text": "➡️ Без цены"}],
            [{"text": "❌ Отменить"}],
        ],
        "resize_keyboard": True,
    }


def contact_step_keyboard():
    return {
        "keyboard": [
            [{"text": "➡️ Без контакта"}],
            [{"text": "❌ Отменить"}],
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


def preview_keyboard(post_id):
    return {
        "inline_keyboard": [
            [
                {
                    "text": "✅ Отправить на модерацию",
                    "callback_data": f"submit:{post_id}",
                }
            ],
            [
                {
                    "text": "❌ Отменить",
                    "callback_data": f"cancel:{post_id}",
                }
            ],
        ]
    }


def baraholka_button():
    return {
        "inline_keyboard": [
            [
                {
                    "text": "📢 Подать объявление",
                    "url": (
                        "https://t.me/"
                        "NhaTrangFairBaraholkaBot?start=newpost"
                    ),
                }
            ]
        ]
    }


def normalize(text):
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    text = text.replace("—", "-").replace("–", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def forbidden_reason(text):
    text = normalize(text)

    if not text:
        return None

    compact = re.sub(r"[\s\-_]+", "", text)

    housing_words = (
        r"(?:квартир\w*|апартамент\w*|студи\w*|комнат\w*|"
        r"дом\w*|вилл\w*|жиль\w*|кондо|condo|apartment|"
        r"studio|room|house|villa)"
    )

    housing_rental_context = (
        r"(?:rent|rental|for\s+rent|renting|"
        r"аренд\w*|сда(?:ю|ем|ет|ется|еться)|"
        r"сдается|сдам|снять|сниму|снимаю|"
        r"посуточн\w*|помесячн\w*|долгосрочн\w*|"
        r"на\s+(?:день|сутки|недел\w*|месяц)|"
        r"cho\s*thu[eê]|thu[eê])"
    )

    if re.search(
        rf"{housing_rental_context}.{{0,120}}{housing_words}",
        text,
        re.I
    ):
        return "аренда квартир/домов"

    if re.search(
        rf"{housing_words}.{{0,120}}{housing_rental_context}",
        text,
        re.I
    ):
        return "аренда квартир/домов"

    if re.search(
        r"\bcho\s*thu[eê]\b.{0,120}"
        r"\b(?:căn\s*hộ|can\s*ho|nhà|phòng|"
        r"studio|villa|chung\s*cư)\b",
        text,
        re.I
    ):
        return "аренда квартир/домов"

    if re.search(
        r"\b(?:căn\s*hộ|can\s*ho|nhà|phòng|"
        r"studio|villa|chung\s*cư)\b.{0,120}"
        r"\b(?:cho\s*thu[eê]|thu[eê])\b",
        text,
        re.I
    ):
        return "аренда квартир/домов"

    bike_rental_alone = [
        r"\brent\b",
        r"\brental\b",
        r"\bfor\s+rent\b",
        r"\brenting\b",
    ]

    for pattern in bike_rental_alone:
        if re.search(pattern, text, re.I):
            return "аренда мотобайков"

    bike_words = (
        r"(?:байк\w*|мотобайк\w*|мотоцикл\w*|мото\w*|"
        r"скутер\w*|мопед\w*|bike|motorbike|motor\s*bike|"
        r"scooter|xe\s*m[aá]y|xe|pcx|airblade|vario|"
        r"vision|lead|nvx|adv|xmax)"
    )

    bike_rental_context = (
        r"(?:rent|rental|for\s+rent|renting|"
        r"аренд\w*|сдам|сдаю|сдается|сдаеться|"
        r"прокат\w*|посуточн\w*|помесячн\w*|"
        r"на\s+(?:день|сутки|недел\w*|месяц)|"
        r"cho\s*thu[eê]|thu[eê])"
    )

    if re.search(
        rf"{bike_rental_context}.{{0,100}}{bike_words}",
        text,
        re.I
    ):
        return "аренда мотобайков"

    if re.search(
        rf"{bike_words}.{{0,100}}{bike_rental_context}",
        text,
        re.I
    ):
        return "аренда мотобайков"

    if re.search(
        r"\b(?:bike|motorbike|motor\s*bike|scooter)\b"
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

    generic_rental_alone = [
        r"\bсдам\b",
        r"\bсдаю\b",
        r"\bсдается\b",
        r"\bсдаеться\b",
        r"\bаренда\b",
        r"\bснять\b",
        r"\bсниму\b",
        r"\bснимаю\b",
        r"\bпосуточно\b",
        r"\bпомесячно\b",
        r"\bдолгосрочно\b",
        r"\bпрокат\w*\b",
    ]

    for pattern in generic_rental_alone:
        if re.search(pattern, text, re.I):
            return "аренда квартир/домов"

    exchange_alone = [
        r"\bобмен\b",
        r"\bобменять\b",
        r"\bобменяю\b",
        r"\bобменя\b",
        r"\bменяю\b",
        r"\bпоменяю\b",
        r"\bexchange\b",
        r"\bcurrency\s+exchange\b",
        r"\bmoney\s+exchange\b",
    ]

    for pattern in exchange_alone:
        if re.search(pattern, text, re.I):
            return "обмен валют"

    currency_words = (
        r"(?:валют\w*|деньг\w*|рубл\w*|доллар\w*|донг\w*|"
        r"евро\w*|usdt|usd|rub|vnd|eur|rmb|юан\w*|"
        r"тенге\w*|currency|money|foreign\s+currency|"
        r"ngoại\s+tệ|ngoai\s+te)"
    )

    if re.search(
        r"(?:рубл\w*|доллар\w*|евро\w*|донг\w*|usd|rub|vnd|eur)"
        r".{0,50}(?:на|в|по)\s+"
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
        r"(?:курс|rate|куплю|продам|обмен|обменять|"
        r"меняю|поменяю|exchange)",
        text,
        re.I
    ):
        return "обмен валют"

    if re.search(
        r"(?:đổi\s+tiền|doi\s+tien|"
        r"đổi\s+ngoại\s+tệ|doi\s+ngoai\s+te|"
        r"mua\s+b[aá]n\s+ngo[aạ]i\s+t[eê])",
        text,
        re.I
    ):
        return "обмен валют"

    if re.search(
        rf"{currency_words}.{{0,80}}"
        r"(?:курс|rate|обмен|exchange|đổi)",
        text,
        re.I
    ):
        return "обмен валют"

    if re.search(
        r"(?:курс|rate|обмен|exchange|đổi).{0,80}"
        rf"{currency_words}",
        text,
        re.I
    ):
        return "обмен валют"

    if re.search(
        r"(?:\bказино\b|\bcasino\b|\bставк\w*\b|"
        r"\bbetting\b|\bsportsbook\b|\b1xbet\b|"
        r"\bpin\s*up\b|\bpinup\b|\bbet\b|"
        r"\bбукмекер\w*\b)",
        text,
        re.I
    ):
        return "казино/ставки"

    crypto = (
        r"(?:крипт\w*|crypto|usdt|bitcoin|btc|"
        r"ethereum|eth|binance|bybit)"
    )

    crypto_promo = (
        r"(?:заработ\w*|инвест\w*|доход\w*|прибыл\w*|"
        r"profit|income|invest\w*|сигнал\w*|гарант\w*|"
        r"пассивн\w*|трейдинг|trading)"
    )

    if re.search(
        rf"{crypto}.{{0,80}}{crypto_promo}",
        text,
        re.I
    ):
        return "криптореклама"

    if re.search(
        rf"{crypto_promo}.{{0,80}}{crypto}",
        text,
        re.I
    ):
        return "криптореклама"

    link_patterns = [
        r"https?://",
        r"www\.",
        r"t\.me/",
        r"telegram\.me/",
        r"telegram\.dog/",
        r"wa\.me/",
        r"chat\.whatsapp\.com/",
        r"discord\.gg/",
        r"vk\.com/",
        r"instagram\.com/",
        r"facebook\.com/",
        r"youtube\.com/",
        r"youtu\.be/",
    ]

    for pattern in link_patterns:
        if re.search(pattern, text, re.I):
            return "ссылка"

    if re.search(r"\bt\s*\.\s*me\s*/", text, re.I):
        return "ссылка"

    if re.search(r"\btelegram\s*\.\s*me\s*/", text, re.I):
        return "ссылка"

    if re.search(r"\bwa\s*\.\s*me\s*/", text, re.I):
        return "ссылка"

    if re.search(r"t\s*\.\s*me", text, re.I):
        return "ссылка"

    if re.search(r"telegram\s*\.\s*me", text, re.I):
        return "ссылка"

    if re.search(r"wa\s*\.\s*me", text, re.I):
        return "ссылка"

    group_promo = [
        r"\bнаша\s+групп\w*",
        r"\bнаши\s+групп\w*",
        r"\bнаш\s+канал\w*",
        r"\bнаши\s+канал\w*",
        r"\bвступайте\s+в\s+(?:нашу\s+|наши\s+)?(?:групп\w*|канал\w*|чат\w*)",
        r"\bвступить\s+в\s+(?:нашу\s+|наши\s+)?(?:групп\w*|канал\w*|чат\w*)",
        r"\bподписывайтесь\s+на\s+(?:канал\w*|групп\w*|чат\w*)",
        r"\bподпишитесь\s+на\s+(?:канал\w*|групп\w*|чат\w*)",
        r"\bтелеграм\s+(?:канал|группа|группу|чат)\b",
        r"\btelegram\s+(?:channel|group|chat)\b",
        r"\bjoin\s+(?:our\s+)?(?:group|channel|chat)\b",
        r"\bнаш\s+(?:telegram|телеграм)\b",
        r"\bссылка\s+на\s+(?:групп\w*|канал\w*|телеграм)\b",
        r"\bзаходите\s+в\s+(?:нашу\s+|наш\s+)?(?:групп\w*|канал\w*|чат\w*)",
        r"\bпереходите\s+в\s+(?:нашу\s+|наш\s+)?(?:групп\w*|канал\w*|чат\w*)",
        r"\bприсоединяйтесь\s+к\s+(?:нашей\s+|нашему\s+|нашу\s+)?(?:групп\w*|канал\w*|чату|группе)",
        r"\bссылка\s+в\s+профиле\b",
        r"\blink\s+in\s+bio\b",
    ]

    for pattern in group_promo:
        if re.search(pattern, text, re.I):
            return "реклама групп/каналов"

    if re.search(
        r"\b(?:реклама|рекламн\w*|advertising|"
        r"advertisement|promo|promotion)\b",
        text,
        re.I
    ):
        return "реклама"

    return None


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


def create_post(user_id):
    user_posts[user_id] = {
        "text": "",
        "photos": [],
        "price": "",
        "contact": "",
        "created": time.time(),
    }


def reset_user(user_id):
    user_states.pop(user_id, None)
    user_posts.pop(user_id, None)


def build_preview(post):
    text = post.get("text", "")
    price = post.get("price", "")
    contact = post.get("contact", "")
    photos = post.get("photos", [])

    result = (
        "👀 ПРЕДПРОСМОТР\n\n"
        f"{text}\n\n"
        f"💰 Цена: {price}\n"
        f"📞 Контакт: {contact}"
    )

    if photos:
        result += f"\n\n📷 Фото: {len(photos)}"

    return result


def build_public_post(post):
    text = post.get("text", "").strip()
    price = post.get("price", "").strip()
    contact = post.get("contact", "").strip()

    result = text

    if price:
        result += f"\n\n💰 Цена: {price}"

    if contact:
        result += f"\n📞 Контакт: {contact}"

    return result


def publish_post(post_id):
    post = user_posts.get(post_id)

    if not post:
        return None

    public_text = build_public_post(post)
    photos = post.get("photos", [])

    if photos:
        result = send_photo(
            GROUP_ID,
            photos[0],
            caption=public_text,
            reply_markup=baraholka_button(),
            message_thread_id=GROUP_THREAD_ID,
        )

        if not result or not result.get("ok"):
            return result

        for photo_id in photos[1:]:
            extra = send_photo(
                GROUP_ID,
                photo_id,
                message_thread_id=GROUP_THREAD_ID,
            )

            if not extra or not extra.get("ok"):
                print(
                    "WARNING: не удалось опубликовать дополнительное фото"
                )

        return result

    return send_message(
        GROUP_ID,
        public_text,
        baraholka_button(),
        GROUP_THREAD_ID,
    )


def send_moderation(user_id):
    post = user_posts.get(user_id)

    if not post:
        return False

    moderation_text = (
        "📢 НОВОЕ ОБЪЯВЛЕНИЕ\n\n"
        f"{post.get('text', '')}\n\n"
        f"💰 Цена: {post.get('price', '')}\n"
        f"📞 Контакт: {post.get('contact', '')}"
    )

    photos = post.get("photos", [])

    if photos:
        moderation_text += f"\n\n📷 Фото: {len(photos)}"

    success = False

    for admin_id in ADMIN_IDS:
        result = send_message(
            admin_id,
            moderation_text,
            moderation_keyboard(user_id),
        )

        if result and result.get("ok"):
            success = True

        for photo_id in photos:
            send_photo(
                admin_id,
                photo_id,
            )

    return success


def ensure_baraholka_button():
    chat = get_chat(GROUP_ID)

    if not chat or not chat.get("ok"):
        print("ERROR: не удалось получить группу")
        return

    pinned = chat["result"].get("pinned_message")

    button_text = (
        "📢 ПОДАТЬ ОБЪЯВЛЕНИЕ В БАРАХОЛКУ\n\n"
        "Нажмите кнопку ниже и отправьте объявление через бота.\n"
        "Все объявления проходят модерацию."
    )

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
                print("Кнопка барахолки обновлена")
                return

    result = send_message(
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
            print("Кнопка барахолки создана и закреплена")
        else:
            print("WARNING: кнопка создана, но не закреплена")
    else:
        print("ERROR: не удалось создать кнопку барахолки")


def start_new_post(user_id):
    create_post(user_id)

    user_states[user_id] = {
        "step": "text"
    }

    send_message(
        user_id,
        "📝 ШАГ 1 ИЗ 4 — ТЕКСТ ОБЪЯВЛЕНИЯ\n\n"
        "Напишите, что вы продаёте, покупаете или отдаёте.\n\n"
        "💡 Пример:\n"
        "Продаю детский велосипед, хорошее состояние, "
        "цена 500 000 VND.",
        text_step_keyboard(),
    )


def handle_private_message(message):
    user = message.get("from", {})
    user_id = user.get("id")

    text = message.get("text", "").strip()

    if not user_id:
        return

    if text.startswith("/start"):
        parts = text.split(maxsplit=1)

        if len(parts) > 1 and parts[1].strip() == "newpost":
            start_new_post(user_id)
            return

        send_message(
            user_id,
            "🏠 Nha Trang Fair Барахолка\n\n"
            "📢 Здесь можно подать объявление о продаже, "
            "покупке или отдаче вещей.\n\n"
            "Все объявления проходят модерацию.",
            main_menu(),
        )
        return

    if text == "📢 Подать объявление":
        start_new_post(user_id)
        return

    if text == "📋 Правила":
        send_message(
            user_id,
            "📋 ПРАВИЛА БАРАХОЛКИ\n\n"
            "Разрешены:\n"
            "• продажа вещей\n"
            "• покупка вещей\n"
            "• отдача вещей\n\n"
            "🚫 Запрещены:\n"
            "• аренда квартир и домов\n"
            "• аренда мотобайков\n"
            "• обмен валют\n"
            "• казино и ставки\n"
            "• криптореклама\n"
            "• реклама групп и каналов\n"
            "• ссылки\n"
            "• спам и флуд\n\n"
            "Все объявления проходят модерацию.",
            main_menu(),
        )
        return

    if text == "❓ Помощь":
        send_message(
            user_id,
            "❓ ПОМОЩЬ\n\n"
            "Нажмите «📢 Подать объявление».\n"
            "Затем бот попросит:\n"
            "1️⃣ текст\n"
            "2️⃣ фото\n"
            "3️⃣ цену\n"
            "4️⃣ контакт\n\n"
            "После этого вы увидите предпросмотр, "
            "а объявление отправится модератору.",
            main_menu(),
        )
        return

    if text == "❌ Отменить":
        reset_user(user_id)

        send_message(
            user_id,
            "❌ Подача объявления отменена.",
            main_menu(),
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

    step = state.get("step")

    if step == "text":
        reason = forbidden_reason(text)

        if reason and not is_admin(user_id):
            reset_user(user_id)

            send_message(
                user_id,
                "🚫 ОБЪЯВЛЕНИЕ НЕ ПРИНЯТО.\n\n"
                f"Причина: {reason}\n\n"
                "Барахолка предназначена только для объявлений "
                "о продаже, покупке или отдаче вещей.",
                main_menu(),
            )
            return

        user_posts[user_id]["text"] = text

        state["step"] = "photos"

        send_message(
            user_id,
            "📷 ШАГ 2 ИЗ 4 — ФОТО\n\n"
            "Отправьте одно или несколько фото объявления.\n\n"
            "Если фото нет — нажмите «➡️ Без фото».\n\n"
            "После отправки фото нажмите «➡️ Готово».",
            photo_step_keyboard(),
        )
        return

    if step == "photos":
        if text == "➡️ Без фото" or text.lower() in (
            "нет",
            "нет фото",
            "без фото",
        ):
            user_posts[user_id]["photos"] = []
            state["step"] = "price"

            send_message(
                user_id,
                "💰 ШАГ 3 ИЗ 4 — ЦЕНА\n\n"
                "Укажите цену.\n\n"
                "💡 Пример: 500 000 VND\n\n"
                "Если цена договорная — нажмите "
                "«➡️ Цена договорная».\n"
                "Если цены нет — нажмите «➡️ Без цены».",
                price_step_keyboard(),
            )
            return

        send_message(
            user_id,
            "📷 Сначала отправьте фото или нажмите "
            "«➡️ Без фото».",
            photo_step_keyboard(),
        )
        return

    if step == "photos_more":
        if text == "➡️ Готово":
            state["step"] = "price"

            send_message(
                user_id,
                "💰 ШАГ 3 ИЗ 4 — ЦЕНА\n\n"
                "Укажите цену.\n\n"
                "💡 Пример: 500 000 VND\n\n"
                "Если цена договорная — нажмите "
                "«➡️ Цена договорная».\n"
                "Если цены нет — нажмите «➡️ Без цены».",
                price_step_keyboard(),
            )
            return

        send_message(
            user_id,
            "📷 Можете отправить ещё фото.\n\n"
            "Когда закончите — нажмите «➡️ Готово».",
            photo_more_keyboard(),
        )
        return

    if step == "price":
        if (
            text == "➡️ Цена договорная"
            or text.lower() == "договорная"
        ):
            user_posts[user_id]["price"] = "Договорная"

        elif text == "➡️ Без цены" or text.lower() in (
            "нет",
            "без цены",
        ):
            user_posts[user_id]["price"] = "Не указана"

        else:
            reason = forbidden_reason(text)

            if reason and not is_admin(user_id):
                reset_user(user_id)

                send_message(
                    user_id,
                    "🚫 Данные не приняты.\n\n"
                    f"Причина: {reason}",
                    main_menu(),
                )
                return

            user_posts[user_id]["price"] = text

        state["step"] = "contact"

        send_message(
            user_id,
            "📞 ШАГ 4 ИЗ 4 — КОНТАКТ\n\n"
            "Укажите контакт для связи.\n\n"
            "💡 Пример: @username или номер телефона.\n\n"
            "Если хотите оставить контакт только через "
            "модерацию — нажмите «➡️ Без контакта».",
            contact_step_keyboard(),
        )
        return

    if step == "contact":
        if text == "➡️ Без контакта" or text.lower() in (
            "нет",
            "без контакта",
        ):
            user_posts[user_id]["contact"] = "В личные сообщения"

        else:
            reason = forbidden_reason(text)

            if reason in (
                "ссылка",
                "реклама групп/каналов",
                "реклама",
                "казино/ставки",
                "криптореклама",
            ) and not is_admin(user_id):
                reset_user(user_id)

                send_message(
                    user_id,
                    "🚫 Контакт не принят.\n\n"
                    f"Причина: {reason}",
                    main_menu(),
                )
                return

            user_posts[user_id]["contact"] = text

        state["step"] = "preview"

        preview = build_preview(
            user_posts[user_id]
        )

        send_message(
            user_id,
            preview + "\n\n"
            "Проверить всё и отправить на модерацию?",
            preview_keyboard(user_id),
        )
        return

    if step == "preview":
        send_message(
            user_id,
            "Нажмите кнопку под предпросмотром.",
        )
        return


def handle_private_photo(message):
    user = message.get("from", {})
    user_id = user.get("id")

    if not user_id:
        return

    state = user_states.get(user_id)

    if not state:
        return

    step = state.get("step")

    if step not in ("photos", "photos_more"):
        return

    photos = message.get("photo", [])

    if not photos:
        return

    photo = photos[-1]

    user_posts.setdefault(
        user_id,
        {
            "text": "",
            "photos": [],
            "price": "",
            "contact": "",
            "created": time.time(),
        }
    )

    user_posts[user_id].setdefault(
        "photos",
        []
    )

    if len(user_posts[user_id]["photos"]) >= 10:
        send_message(
            user_id,
            "⚠️ Можно добавить максимум 10 фото.\n\n"
            "Нажмите «➡️ Готово».",
            photo_more_keyboard(),
        )
        state["step"] = "photos_more"
        return

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
        "Можете отправить ещё фото или нажать "
        "«➡️ Готово».",
        photo_more_keyboard(),
    )


def handle_callback(callback):
    callback_id = callback.get("id")
    data = callback.get("data", "")
    from_user = callback.get("from", {})
    user_id = from_user.get("id")

    answer_callback(callback_id)

    if data.startswith("submit:"):
        try:
            post_id = int(data.split(":", 1)[1])
        except Exception:
            return

        if post_id != user_id:
            return

        post = user_posts.get(post_id)

        if not post:
            send_message(
                user_id,
                "❌ Объявление не найдено.",
                main_menu(),
            )
            return

        reason = forbidden_reason(
            post.get("text", "")
        )

        if reason and not is_admin(user_id):
            reset_user(user_id)

            send_message(
                user_id,
                "🚫 Объявление не принято.\n\n"
                f"Причина: {reason}",
                main_menu(),
            )
            return

        if not ADMIN_IDS:
            send_message(
                user_id,
                "⚠️ Сейчас не настроен модератор. "
                "Объявление не отправлено.",
                main_menu(),
            )
            return

        if send_moderation(user_id):
            user_states.pop(user_id, None)

            send_message(
                user_id,
                "✅ Объявление отправлено на модерацию.\n\n"
                "После проверки модератором оно будет опубликовано.",
                main_menu(),
            )
        else:
            send_message(
                user_id,
                "⚠️ Не удалось отправить объявление модератору. "
                "Попробуйте ещё раз.",
                main_menu(),
            )

        return

    if data.startswith("cancel:"):
        try:
            post_id = int(data.split(":", 1)[1])
        except Exception:
            return

        if post_id != user_id:
            return

        reset_user(user_id)

        send_message(
            user_id,
            "❌ Подача объявления отменена.",
            main_menu(),
        )
        return

    if not is_admin(user_id):
        return

    if data.startswith("approve:"):
        try:
            post_id = int(data.split(":", 1)[1])
        except Exception:
            return

        post = user_posts.get(post_id)

        if not post:
            send_message(
                user_id,
                "❌ Объявление уже обработано.",
            )
            return

        reason = forbidden_reason(
            post.get("text", "")
        )

        if reason:
            send_message(
                user_id,
                "🚫 Публикация остановлена фильтром.\n\n"
                f"Причина: {reason}",
            )

            send_message(
                post_id,
                "❌ Ваше объявление не может быть опубликовано.\n\n"
                f"Причина: {reason}",
                main_menu(),
            )

            reset_user(post_id)
            return

        result = publish_post(post_id)

        if result and result.get("ok"):
            send_message(
                post_id,
                "✅ Ваше объявление опубликовано в теме «Барахолка».",
                main_menu(),
            )

            reset_user(post_id)

            send_message(
                user_id,
                f"✅ Объявление пользователя {post_id} опубликовано.",
            )

        else:
            send_message(
                user_id,
                "❌ Не удалось опубликовать объявление. "
                "Проверьте права бота и тему «Барахолка».",
            )

        return

    if data.startswith("reject:"):
        try:
            post_id = int(data.split(":", 1)[1])
        except Exception:
            return

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
            main_menu(),
        )

        reset_user(post_id)

        send_message(
            user_id,
            f"❌ Объявление пользователя {post_id} отклонено.",
        )

        return

    if data.startswith("ban:"):
        try:
            post_id = int(data.split(":", 1)[1])
        except Exception:
            return

        post = user_posts.get(post_id)

        if not post:
            send_message(
                user_id,
                "❌ Объявление уже обработано.",
            )
            return

        result = ban_user(
            GROUP_ID,
            post_id,
        )

        if result and result.get("ok"):
            send_message(
                user_id,
                f"🚫 Пользователь {post_id} заблокирован.",
            )

            send_message(
                post_id,
                "🚫 Вы заблокированы в группе за нарушение правил.",
                main_menu(),
            )

            reset_user(post_id)
        else:
            send_message(
                user_id,
                "❌ Не удалось заблокировать пользователя.",
            )

        return


def handle_group_message(message):
    chat = message.get("chat", {})
    chat_id = str(chat.get("id"))

    if chat_id != GROUP_ID:
        return

    user = message.get("from", {})
    user_id = user.get("id")

    if not user_id:
        return

    if is_admin(user_id):
        return

    if is_chat_admin(GROUP_ID, user_id):
        return

    text = message.get("text", "")

    if not text:
        return

    reason = forbidden_reason(text)

    if reason:
        message_id = message.get("message_id")

        if message_id:
            delete_message(
                GROUP_ID,
                message_id,
            )

        print(
            f"Удалено сообщение {message_id}: {reason}"
        )
        return

    if not flood_check(user_id):
        message_id = message.get("message_id")

        if message_id:
            delete_message(
                GROUP_ID,
                message_id,
            )

        return


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

    if chat_type in ("group", "supergroup"):
        handle_group_message(message)


def main():
    print("======================================")
    print("Nha Trang Fair Барахолка Bot")
    print("======================================")

    me = get_me()

    if not me or not me.get("ok"):
        print("ERROR: Telegram API недоступен")
        return

    bot = me["result"]

    print(
        "Bot:",
        bot.get("first_name"),
        "@",
        bot.get("username")
    )

    print("GROUP_ID:", GROUP_ID)
    print("GROUP_THREAD_ID:", GROUP_THREAD_ID)
    print("ADMIN_IDS:", ADMIN_IDS)

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
                }
            )

            if not result or not result.get("ok"):
                time.sleep(3)
                continue

            for update in result.get("result", []):
                offset = update["update_id"] + 1

                try:
                    process_update(update)
                except Exception as e:
                    print(
                        "UPDATE ERROR:",
                        repr(e)
                    )

        except Exception as e:
            print(
                "MAIN LOOP ERROR:",
                repr(e)
            )

            time.sleep(5)


if __name__ == "__main__":
    main()
