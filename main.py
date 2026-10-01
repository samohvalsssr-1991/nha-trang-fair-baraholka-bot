
import os
import re
import json
import time
import urllib.request
import urllib.parse

# ============================================================
# NHA TRANG FAIR БАРАХОЛКА — FINAL BOT
# ============================================================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

# Точные данные группы/темы, которые мы получили из Telegram.
GROUP_ID = "-1001776236864"
GROUP_THREAD_ID = "17186"

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

API = f"https://api.telegram.org/bot{TOKEN}"

users = {}
pending_posts = {}
flood = {}
admin_cache = {}
BOT_ID = None


# ============================================================
# TELEGRAM API
# ============================================================

def api(method, data=None):
    data = data or {}
    encoded = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(f"{API}/{method}", data=encoded)

    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode())


def send_message(chat_id, text, keyboard=None, message_thread_id=None):
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }

    if message_thread_id:
        data["message_thread_id"] = int(message_thread_id)

    if keyboard:
        data["reply_markup"] = json.dumps(keyboard, ensure_ascii=False)

    return api("sendMessage", data)


def edit_message(chat_id, message_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
    }

    if keyboard:
        data["reply_markup"] = json.dumps(keyboard, ensure_ascii=False)

    return api("editMessageText", data)


def delete_message(chat_id, message_id):
    try:
        api("deleteMessage", {
            "chat_id": chat_id,
            "message_id": message_id
        })
    except Exception:
        pass


def pin_message(chat_id, message_id):
    try:
        return api("pinChatMessage", {
            "chat_id": chat_id,
            "message_id": message_id,
            "disable_notification": True
        })
    except Exception as e:
        print("Pin error:", e)
        return {"ok": False}


def ban_user(chat_id, user_id):
    try:
        return api("banChatMember", {
            "chat_id": chat_id,
            "user_id": user_id
        })
    except Exception as e:
        print("Ban error:", e)
        return {"ok": False}


def answer_callback(callback_id, text=""):
    try:
        api("answerCallbackQuery", {
            "callback_query_id": callback_id,
            "text": text
        })
    except Exception:
        pass


def get_me():
    global BOT_ID
    result = api("getMe")
    if result.get("ok"):
        BOT_ID = result["result"]["id"]
        return result["result"]
    return None


# ============================================================
# RIGHTS / ADMINS
# ============================================================

def is_configured_admin(user_id):
    return user_id in ADMIN_IDS


def is_group_admin(user_id):
    if user_id in ADMIN_IDS:
        return True

    now = time.time()
    cached = admin_cache.get(user_id)

    if cached and now - cached["time"] < 300:
        return cached["value"]

    try:
        result = api("getChatMember", {
            "chat_id": GROUP_ID,
            "user_id": user_id
        })

        status = result.get("result", {}).get("status")
        value = status in ("administrator", "creator")

        admin_cache[user_id] = {
            "value": value,
            "time": now
        }

        return value

    except Exception:
        return False


# ============================================================
# BUTTONS
# ============================================================

def main_menu():
    return {
        "inline_keyboard": [
            [{"text": "📢 Подать объявление", "callback_data": "new_post"}],
            [
                {"text": "📋 Правила", "callback_data": "rules"},
                {"text": "❓ Помощь", "callback_data": "help"}
            ]
        ]
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
                    "callback_data": f"block:{post_id}"
                }
            ]
        ]
    }


def submission_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "✅ Готово с фото", "callback_data": "photos_done"}],
            [{"text": "➡️ Без фото", "callback_data": "no_photos"}]
        ]
    }


def baraholka_button():
    return {
        "inline_keyboard": [[
            {
                "text": "📢 Подать объявление",
                "url": "https://t.me/NhaTrangFairBaraholkaBot?start=newpost"
            }
        ]]
    }


# ============================================================
# FILTER
# ============================================================

def normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


def forbidden_reason(text):
    text = normalize(text)

    patterns = [
        (
            r"(аренд|сдам|сниму).{0,60}(квартир|дом|комнат|апартамент)"
            r"|"
            r"(квартир|дом|комнат|апартамент).{0,60}(аренд|сдам|сниму)"
            r"|"
            r"cho thuê căn hộ|cho thuê nhà|cho thue can ho|cho thue nha",
            "аренда квартир/домов"
        ),
        (
            r"(аренд|сдам).{0,60}(мотобайк|мото|скутер|байк)"
            r"|"
            r"(motobike|motorbike|bike|scooter).{0,40}(rent|rental)"
            r"|"
            r"cho thuê xe máy|cho thue xe may",
            "аренда мотобайков"
        ),
        (
            r"обмен.{0,50}(валют|денег|доллар|донг)"
            r"|"
            r"(валют|доллар|донг).{0,50}обмен"
            r"|"
            r"(currency exchange|money exchange|exchange)"
            r"|"
            r"đổi tiền|đổi ngoại tệ|doi tien",
            "обмен валют"
        ),
        (
            r"казино|casino|ставки|betting|1xbet|pin up|pinup|bet",
            "казино/ставки"
        ),
        (
            r"(крипт|crypto|usdt|bitcoin|btc|eth).{0,50}"
            r"(заработ|инвест|доход|прибыл|profit|income|invest)"
            r"|"
            r"(заработ|инвест|доход|прибыл|profit|income|invest).{0,50}"
            r"(крипт|crypto|usdt|bitcoin|btc|eth)",
            "криптореклама"
        ),
        (
            r"подписывайтесь|подпишись|реклама|рекламн|promo|advertising",
            "реклама"
        ),
        (
            r"https?://|www\.|t\.me/|telegram\.me/|wa\.me/",
            "ссылка"
        ),
    ]

    for pattern, reason in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return reason

    return None


def flood_check(user_id):
    now = time.time()
    times = flood.setdefault(user_id, [])
    times[:] = [x for x in times if now - x < 15]
    times.append(now)
    return len(times) >= 7


# ============================================================
# POST FLOW
# ============================================================

def create_post(user_id):
    pending_posts[user_id] = {
        "text": "",
        "photos": [],
        "price": "",
        "contact": "",
        "step": "text",
        "created": time.time(),
        "user_id": user_id
    }


def publish_post(post):
    caption = (
        "📢 <b>ОБЪЯВЛЕНИЕ</b>\n\n"
        f"{post['text']}\n\n"
        f"💰 <b>Цена:</b> {post['price']}\n"
        f"📞 <b>Контакт:</b> {post['contact']}"
    )

    thread_id = int(GROUP_THREAD_ID)
    photos = post.get("photos", [])

    try:
        if photos:
            media = []

            for index, photo_id in enumerate(photos[:10]):
                item = {
                    "type": "photo",
                    "media": photo_id
                }

                if index == 0:
                    item["caption"] = caption
                    item["parse_mode"] = "HTML"

                media.append(item)

            result = api("sendMediaGroup", {
                "chat_id": GROUP_ID,
                "message_thread_id": thread_id,
                "media": json.dumps(media, ensure_ascii=False)
            })

        else:
            result = api("sendMessage", {
                "chat_id": GROUP_ID,
                "message_thread_id": thread_id,
                "text": caption,
                "parse_mode": "HTML"
            })

        if result.get("ok"):
            print(
                f"Published: group={GROUP_ID}, topic={GROUP_THREAD_ID}"
            )
            return True

        print("Publish error:", result)
        return False

    except Exception as e:
        print("Publish exception:", e)
        return False


def send_moderation(post_id, post):
    if not ADMIN_IDS:
        print("ERROR: ADMIN_IDS is empty")
        return

    caption = (
        "🔔 <b>НОВОЕ ОБЪЯВЛЕНИЕ НА МОДЕРАЦИИ</b>\n\n"
        f"📝 <b>Текст:</b>\n{post['text']}\n\n"
        f"💰 <b>Цена:</b> {post['price']}\n"
        f"📞 <b>Контакт:</b> {post['contact']}\n\n"
        f"🆔 ID заявки: <code>{post_id}</code>"
    )

    for admin_id in ADMIN_IDS:
        try:
            if post["photos"]:
                media = []

                for index, photo_id in enumerate(post["photos"][:10]):
                    item = {
                        "type": "photo",
                        "media": photo_id
                    }

                    if index == 0:
                        item["caption"] = caption
                        item["parse_mode"] = "HTML"

                    media.append(item)

                api("sendMediaGroup", {
                    "chat_id": admin_id,
                    "media": json.dumps(media, ensure_ascii=False)
                })

                send_message(
                    admin_id,
                    "Выберите действие:",
                    moderation_keyboard(post_id)
                )

            else:
                send_message(
                    admin_id,
                    caption,
                    moderation_keyboard(post_id)
                )

        except Exception as e:
            print("Moderation error:", e)


# ============================================================
# AUTO BUTTON — ONE PINNED MESSAGE
# ============================================================

def ensure_baraholka_button():
    """
    Creates one permanent button message in topic 17186.
    On restart, if that message is the pinned message, edits it
    instead of creating another copy.
    """

    if not GROUP_ID or not GROUP_THREAD_ID:
        print("Button skipped: group/topic not configured")
        return

    button_text = (
        "📢 <b>Хотите разместить объявление?</b>\n\n"
        "Нажмите кнопку ниже.\n"
        "Объявление сначала проходит модерацию, "
        "после одобрения автоматически публикуется "
        "в разделе «Барахолка»."
    )

    try:
        chat = api("getChat", {"chat_id": GROUP_ID})

        if not chat.get("ok"):
            print("getChat error:", chat)
            return

        pinned = chat["result"].get("pinned_message")

        if (
            pinned
            and pinned.get("from", {}).get("id") == BOT_ID
            and "Хотите разместить объявление?" in
                pinned.get("text", "")
        ):
            edit_message(
                GROUP_ID,
                pinned["message_id"],
                button_text,
                baraholka_button()
            )
            print("Baraholka button: existing pinned message updated")
            return

        result = send_message(
            GROUP_ID,
            button_text,
            baraholka_button(),
            message_thread_id=GROUP_THREAD_ID
        )

        if result.get("ok"):
            message_id = result["result"]["message_id"]
            pin_result = pin_message(GROUP_ID, message_id)

            if pin_result.get("ok"):
                print("Baraholka button: created and pinned")
            else:
                print("Baraholka button: created, but pin failed")
        else:
            print("Baraholka button send error:", result)

    except Exception as e:
        print("Button setup error:", e)


# ============================================================
# PRIVATE CHAT
# ============================================================

def handle_private_message(message):
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "").strip()

    if text.startswith("/start"):
        users[user_id] = {"step": None}

        if text.strip() == "/start newpost":
            create_post(user_id)
            send_message(
                chat_id,
                "📝 <b>Шаг 1 из 4</b>\n\n"
                "Напишите текст объявления.\n\n"
                "Например:\n"
                "«Продаю детский велосипед, состояние хорошее...»"
            )
            return

        send_message(
            chat_id,
            "👋 <b>Добро пожаловать!</b>\n\n"
            "Это бот барахолки Нячанга.\n\n"
            "Здесь можно подать объявление о продаже, покупке "
            "или отдаче вещей.\n\n"
            "Все объявления проходят модерацию.",
            main_menu()
        )
        return

    if text == "/id":
        send_message(
            chat_id,
            f"🆔 Ваш Telegram ID:\n<code>{user_id}</code>\n\n"
            f"🆔 Chat ID:\n<code>{chat_id}</code>"
        )
        return

    if text == "/rules":
        send_message(
            chat_id,
            "📋 <b>Правила барахолки</b>\n\n"
            "Разрешены объявления о продаже, покупке и отдаче вещей.\n\n"
            "🚫 Запрещены:\n"
            "• аренда квартир и домов\n"
            "• аренда мотобайков\n"
            "• обмен валют\n"
            "• казино и ставки\n"
            "• криптореклама\n"
            "• спам и флуд\n"
            "• рекламные ссылки"
        )
        return

    state = pending_posts.get(user_id)

    if not state:
        send_message(chat_id, "Выберите действие:", main_menu())
        return

    if state["step"] == "text":
        if not text:
            send_message(chat_id, "❗ Напишите текст объявления.")
            return

        reason = forbidden_reason(text)

        if reason:
            pending_posts.pop(user_id, None)
            send_message(
                chat_id,
                f"❌ Объявление нельзя подать.\n\n"
                f"Причина: <b>{reason}</b>\n\n"
                "Этот раздел предназначен только для барахолки."
            )
            return

        state["text"] = text
        state["step"] = "photos"

        send_message(
            chat_id,
            "📸 Теперь отправьте фотографии товара.\n\n"
            "Можно отправить несколько фотографий.\n"
            "Когда закончите — нажмите <b>«Готово с фото»</b>.\n\n"
            "Если фотографий нет — нажмите <b>«Без фото»</b>.",
            submission_keyboard()
        )
        return

    if state["step"] == "price":
        if not text:
            send_message(chat_id, "❗ Напишите цену.")
            return

        state["price"] = text
        state["step"] = "contact"

        send_message(
            chat_id,
            "📞 Теперь отправьте контакт для связи.\n\n"
            "Например: Telegram username, телефон или другой способ связи."
        )
        return

    if state["step"] == "contact":
        if not text:
            send_message(chat_id, "❗ Укажите контакт.")
            return

        state["contact"] = text
        state["step"] = "preview"

        preview = (
            "👀 <b>ПРОВЕРЬТЕ ОБЪЯВЛЕНИЕ</b>\n\n"
            f"{state['text']}\n\n"
            f"💰 <b>Цена:</b> {state['price']}\n"
            f"📞 <b>Контакт:</b> {state['contact']}\n\n"
            "После отправки объявление попадёт модератору."
        )

        send_message(
            chat_id,
            preview,
            {
                "inline_keyboard": [
                    [
                        {
                            "text": "📤 Отправить модератору",
                            "callback_data": "send_moderation"
                        }
                    ],
                    [
                        {
                            "text": "❌ Отменить",
                            "callback_data": "cancel_post"
                        }
                    ]
                ]
            }
        )


def handle_private_photo(message):
    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]

    state = pending_posts.get(user_id)

    if not state or state["step"] != "photos":
        return

    photos = message.get("photo", [])

    if photos:
        state["photos"].append(photos[-1]["file_id"])

        send_message(
            chat_id,
            f"📸 Фото добавлено. Всего фотографий: "
            f"<b>{len(state['photos'])}</b>\n\n"
            "Можете отправить ещё фото или нажмите "
            "«Готово с фото».",
            submission_keyboard()
        )


# ============================================================
# CALLBACKS
# ============================================================

def handle_callback(query):
    callback_id = query["id"]
    data = query.get("data", "")
    user_id = query["from"]["id"]
    chat_id = query["message"]["chat"]["id"]

    answer_callback(callback_id)

    if data == "new_post":
        create_post(user_id)
        send_message(
            chat_id,
            "📝 <b>Шаг 1 из 4</b>\n\n"
            "Напишите текст объявления.\n\n"
            "Например:\n"
            "«Продаю детский велосипед, состояние хорошее...»"
        )
        return

    if data == "rules":
        send_message(
            chat_id,
            "📋 <b>Правила барахолки</b>\n\n"
            "Разрешены продажа, покупка и отдача вещей.\n\n"
            "🚫 Запрещены аренда квартир/домов, "
            "аренда мотобайков, обмен валют, казино, "
            "криптореклама, спам и ссылки."
        )
        return

    if data == "help":
        send_message(
            chat_id,
            "❓ <b>Помощь</b>\n\n"
            "Нажмите «📢 Подать объявление» и следуйте инструкциям."
        )
        return

    if data == "photos_done":
        state = pending_posts.get(user_id)

        if not state:
            return

        state["step"] = "price"

        send_message(
            chat_id,
            "💰 <b>Шаг 3 из 4</b>\n\n"
            "Укажите цену.\n\n"
            "Например: 500.000 VND"
        )
        return

    if data == "no_photos":
        state = pending_posts.get(user_id)

        if not state:
            return

        state["photos"] = []
        state["step"] = "price"

        send_message(
            chat_id,
            "💰 <b>Шаг 3 из 4</b>\n\n"
            "Укажите цену."
        )
        return

    if data == "cancel_post":
        pending_posts.pop(user_id, None)

        send_message(
            chat_id,
            "❌ Объявление отменено.",
            main_menu()
        )
        return

    if data == "send_moderation":
        state = pending_posts.get(user_id)

        if not state:
            send_message(chat_id, "❌ Заявка не найдена.")
            return

        post_id = f"{user_id}_{int(time.time())}"

        state["step"] = "moderation"
        state["user_id"] = user_id

        pending_posts[post_id] = state
        pending_posts.pop(user_id, None)

        send_moderation(post_id, state)

        send_message(
            chat_id,
            "✅ Объявление отправлено на модерацию.\n\n"
            "После проверки модератором оно будет опубликовано."
        )
        return

    if ":" in data:
        action, post_id = data.split(":", 1)

        if not is_configured_admin(user_id):
            answer_callback(
                callback_id,
                "⛔ Только для модераторов."
            )
            return

        post = pending_posts.get(post_id)

        if not post:
            send_message(chat_id, "❌ Заявка уже обработана.")
            return

        if action == "approve":
            success = publish_post(post)

            if success:
                pending_posts.pop(post_id, None)

                send_message(
                    chat_id,
                    f"✅ Объявление <code>{post_id}</code> опубликовано."
                )

                try:
                    send_message(
                        post["user_id"],
                        "🎉 <b>Ваше объявление опубликовано!</b>"
                    )
                except Exception:
                    pass

            else:
                send_message(
                    chat_id,
                    "❌ Не удалось опубликовать объявление."
                )

        elif action == "reject":
            pending_posts.pop(post_id, None)

            send_message(
                chat_id,
                f"❌ Объявление <code>{post_id}</code> отклонено."
            )

            try:
                send_message(
                    post["user_id"],
                    "❌ Ваше объявление отклонено модератором."
                )
            except Exception:
                pass

        elif action == "block":
            pending_posts.pop(post_id, None)

            ban_result = ban_user(GROUP_ID, post["user_id"])

            if ban_result.get("ok"):
                result_text = (
                    f"🚫 Объявление отклонено.\n"
                    f"Пользователь заблокирован в группе."
                )
            else:
                result_text = (
                    f"🚫 Объявление отклонено.\n"
                    f"⚠️ Заблокировать пользователя не удалось."
                )

            send_message(chat_id, result_text)

            try:
                send_message(
                    post["user_id"],
                    "🚫 Ваше объявление отклонено."
                )
            except Exception:
                pass


# ============================================================
# GROUP
# ============================================================

def handle_group_message(message):
    chat_id = str(message["chat"]["id"])
    user = message.get("from", {})
    user_id = user.get("id")

    if chat_id != GROUP_ID or not user_id:
        return

    # Все реальные администраторы группы исключены из фильтра.
    if is_group_admin(user_id):
        return

    text = message.get("text", "") or message.get("caption", "")

    if text:
        reason = forbidden_reason(text)

        if reason:
            delete_message(chat_id, message["message_id"])

            try:
                thread_id = message.get("message_thread_id")

                send_message(
                    chat_id,
                    f"🚫 Сообщение удалено.\n"
                    f"Причина: <b>{reason}</b>.",
                    message_thread_id=thread_id
                )
            except Exception:
                pass

            return

    if flood_check(user_id):
        delete_message(chat_id, message["message_id"])


# ============================================================
# UPDATES
# ============================================================

def process_update(update):
    if "callback_query" in update:
        handle_callback(update["callback_query"])
        return

    message = update.get("message")

    if not message:
        return

    chat_type = message["chat"].get("type")

    if chat_type == "private":
        if "photo" in message:
            handle_private_photo(message)
        else:
            handle_private_message(message)

    elif chat_type in ("group", "supergroup"):
        text = message.get("text", "").strip()

        # /id отвечает именно в той теме, откуда команда пришла.
        if text.startswith("/id"):
            send_message(
                message["chat"]["id"],
                f"🆔 Chat ID:\n"
                f"<code>{message['chat']['id']}</code>\n\n"
                f"🆔 Topic ID:\n"
                f"<code>{message.get('message_thread_id', 'нет')}</code>",
                message_thread_id=message.get("message_thread_id")
            )
            return

        handle_group_message(message)


# ============================================================
# MAIN
# ============================================================

def main():
    if not TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN is missing")
        return

    me = get_me()

    if not me:
        print("ERROR: bot authorization failed")
        return

    print("Bot started")
    print(f"Bot: @{me.get('username')}")
    print(f"GROUP_ID: {GROUP_ID}")
    print(f"GROUP_THREAD_ID: {GROUP_THREAD_ID}")
    print(f"ADMIN_IDS: {sorted(ADMIN_IDS)}")

    # Создаём/обновляем одну кнопку в теме.
    ensure_baraholka_button()

    offset = 0

    while True:
        try:
            result = api("getUpdates", {
                "offset": offset,
                "timeout": 30,
                "allowed_updates": json.dumps([
                    "message",
                    "callback_query"
                ])
            })

            for update in result.get("result", []):
                offset = update["update_id"] + 1

                try:
                    process_update(update)
                except Exception as e:
                    print("Update error:", e)

        except Exception as e:
            print("Connection error:", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
