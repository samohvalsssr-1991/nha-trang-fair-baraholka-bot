import os
import re
import json
import time
import urllib.request
import urllib.parse

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

GROUP_ID = os.getenv("GROUP_ID", "").strip()
GROUP_THREAD_ID = os.getenv("GROUP_THREAD_ID", "").strip()

API = f"https://api.telegram.org/bot{TOKEN}"

users = {}
pending_posts = {}
flood = {}


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


def delete_message(chat_id, message_id):
    try:
        api("deleteMessage", {
            "chat_id": chat_id,
            "message_id": message_id
        })
    except Exception:
        pass


def answer_callback(callback_id, text=""):
    try:
        api("answerCallbackQuery", {
            "callback_query_id": callback_id,
            "text": text
        })
    except Exception:
        pass


def is_admin(user_id):
    return user_id in ADMIN_IDS


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
                {"text": "✅ Опубликовать", "callback_data": f"approve:{post_id}"},
                {"text": "❌ Отклонить", "callback_data": f"reject:{post_id}"}
            ],
            [{"text": "🚫 Заблокировать", "callback_data": f"block:{post_id}"}]
        ]
    }


def submission_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "✅ Готово с фото", "callback_data": "photos_done"}],
            [{"text": "➡️ Без фото", "callback_data": "no_photos"}]
        ]
    }


def normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


def forbidden_reason(text):
    text = normalize(text)

    patterns = [
        (
            r"(аренд|сдам|сниму).{0,40}(квартир|дом|комнат|апартамент)"
            r"|"
            r"(квартир|дом|комнат|апартамент).{0,40}(аренд|сдам|сниму)",
            "аренда квартир/домов"
        ),
        (
            r"(аренд|сдам).{0,40}(мотобайк|мото|скутер|байк)"
            r"|"
            r"(motobike|motorbike|bike).{0,30}(rent|rental)"
            r"|"
            r"cho thuê xe máy",
            "аренда мотобайков"
        ),
        (
            r"обмен.{0,30}(валют|денег|доллар|донг)"
            r"|"
            r"(currency exchange|money exchange)"
            r"|"
            r"đổi tiền|đổi ngoại tệ",
            "обмен валют"
        ),
        (
            r"казино|casino|ставки|betting|1xbet|pin up|pinup",
            "казино/ставки"
        ),
        (
            r"заработок.{0,30}(крипт|usdt|bitcoin)"
            r"|"
            r"крипт.{0,30}(заработ|инвест)"
            r"|"
            r"crypto.{0,30}(profit|income|invest)",
            "криптореклама"
        ),
        (
            r"подписывайтесь|подпишись|реклама|рекламн",
            "реклама"
        ),
        (
            r"https?://|www\.|t\.me/",
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


def create_post(user_id):
    pending_posts[user_id] = {
        "text": "",
        "photos": [],
        "price": "",
        "contact": "",
        "step": "text",
        "created": time.time()
    }


def publish_post(post):
    if not GROUP_ID:
        print("ERROR: GROUP_ID is missing")
        return False

    chat_id = GROUP_ID

    caption = (
        "📢 <b>ОБЪЯВЛЕНИЕ</b>\n\n"
        f"{post['text']}\n\n"
        f"💰 <b>Цена:</b> {post['price']}\n"
        f"📞 <b>Контакт:</b> {post['contact']}"
    )

    photos = post.get("photos", [])

    try:
        thread_id = GROUP_THREAD_ID.strip()

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

            data = {
                "chat_id": chat_id,
                "media": json.dumps(media, ensure_ascii=False)
            }

            if thread_id:
                data["message_thread_id"] = int(thread_id)

            result = api("sendMediaGroup", data)

        else:
            data = {
                "chat_id": chat_id,
                "text": caption,
                "parse_mode": "HTML"
            }

            if thread_id:
                data["message_thread_id"] = int(thread_id)

            result = api("sendMessage", data)

        if not result.get("ok"):
            print("Publish error:", result)
            return False

        print(
            f"Published to {chat_id}"
            + (f", topic {thread_id}" if thread_id else ", General")
        )
        return True

    except Exception as e:
        print("Publish exception:", e)
        return False


def send_moderation(post_id, post):
    if not ADMIN_IDS:
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
            print("Moderation send error:", e)


def handle_private_message(message):
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "").strip()

    if text == "/start":
        users[user_id] = {"step": None}
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

    step = state["step"]

    if step == "text":
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

    if step == "price":
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

    if step == "contact":
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
                    [{"text": "📤 Отправить модератору", "callback_data": "send_moderation"}],
                    [{"text": "❌ Отменить", "callback_data": "cancel_post"}]
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
        photo_id = photos[-1]["file_id"]
        state["photos"].append(photo_id)

        send_message(
            chat_id,
            f"📸 Фото добавлено. Всего фотографий: <b>{len(state['photos'])}</b>\n\n"
            "Можете отправить ещё фото или нажмите «Готово с фото».",
            submission_keyboard()
        )


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
            "🚫 Запрещены аренда недвижимости, "
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

        if not is_admin(user_id):
            answer_callback(callback_id, "⛔ Только для модераторов.")
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
                    "❌ Не удалось опубликовать объявление.\n"
                    "Проверьте GROUP_ID и GROUP_THREAD_ID."
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

            send_message(
                chat_id,
                f"🚫 Заявка <code>{post_id}</code> отклонена."
            )

            try:
                send_message(
                    post["user_id"],
                    "🚫 Ваше объявление заблокировано."
                )
            except Exception:
                pass


def handle_group_message(message):
    chat_id = message["chat"]["id"]
    user = message.get("from", {})
    user_id = user.get("id")

    if not user_id:
        return

    if is_admin(user_id):
        return

    text = message.get("text", "") or message.get("caption", "")

    if text:
        reason = forbidden_reason(text)

        if reason:
            delete_message(chat_id, message["message_id"])

            try:
                send_message(
                    chat_id,
                    f"🚫 Сообщение удалено.\nПричина: <b>{reason}</b>."
                )
            except Exception:
                pass

            return

    if flood_check(user_id):
        delete_message(chat_id, message["message_id"])


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
        # /id теперь работает и в группе, чтобы при необходимости
        # можно было узнать числовой Chat ID без сторонних ботов.
        text = message.get("text", "").strip()

        if text == "/id":
            send_message(
                message["chat"]["id"],
                f"🆔 Chat ID:\n<code>{message['chat']['id']}</code>\n\n"
                f"🆔 Topic ID:\n<code>{message.get('message_thread_id', 'нет')}</code>"
            )
            return

        handle_group_message(message)


def main():
    if not TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN is missing")
        return

    print("Bot started")
    print(f"GROUP_ID: {GROUP_ID or 'NOT SET'}")
    print(f"GROUP_THREAD_ID: {GROUP_THREAD_ID or 'NOT SET'}")

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
