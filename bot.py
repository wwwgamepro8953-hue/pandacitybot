import os
import logging
import requests
from flask import Flask, request

# =========================
# تنظیمات
# =========================

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL = os.environ.get("CHANNEL", "@StoreAgaAli").strip()
RENDER_URL = os.environ["RENDER_EXTERNAL_URL"].rstrip("/")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# =========================
# Logging
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# =========================
# Flask
# =========================

app = Flask(__name__)


# =========================
# Telegram API
# =========================

def telegram(method, data=None):
    try:
        response = requests.post(
            f"{TELEGRAM_API}/{method}",
            json=data or {},
            timeout=30
        )

        response.raise_for_status()
        result = response.json()

        if not result.get("ok"):
            logger.error(
                "Telegram API error: %s",
                result
            )

        return result

    except requests.RequestException as error:
        logger.exception(
            "Telegram request failed: %s",
            error
        )
        return {
            "ok": False,
            "error": str(error)
        }


# =========================
# ارسال پیام
# =========================

def send_message(chat_id, text, keyboard=None):

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = {
            "inline_keyboard": keyboard
        }

    return telegram("sendMessage", data)


# =========================
# بررسی عضویت
# =========================

def is_member(user_id):

    result = telegram(
        "getChatMember",
        {
            "chat_id": CHANNEL,
            "user_id": user_id
        }
    )

    if not result.get("ok"):
        logger.error(
            "Could not check membership: %s",
            result
        )
        return False

    status = result["result"]["status"]

    logger.info(
        "User %s membership status: %s",
        user_id,
        status
    )

    return status in {
        "member",
        "administrator",
        "creator"
    }


# =========================
# پیام شروع
# =========================

def start_message(chat_id):

    channel_username = CHANNEL.lstrip("@")

    keyboard = [
        [
            {
                "text": "📢 عضویت در کانال",
                "url": f"https://t.me/{channel_username}"
            }
        ],
        [
            {
                "text": "✅ بررسی عضویت",
                "callback_data": "check_membership"
            }
        ]
    ]

    send_message(
        chat_id,
        "🐼 سلام!\n\n"
        "برای ادامه ابتدا عضو کانال زیر شو، "
        "سپس روی «بررسی عضویت» بزن 👇",
        keyboard
    )


# =========================
# پردازش Update تلگرام
# =========================

def handle_update(update):

    # -------------------------
    # پیام معمولی
    # -------------------------

    if "message" in update:

        message = update["message"]

        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        if text.startswith("/start"):

            logger.info(
                "Start received from user %s",
                chat_id
            )

            start_message(chat_id)

            return

    # -------------------------
    # Callback Query
    # -------------------------

    if "callback_query" in update:

        callback = update["callback_query"]

        callback_id = callback["id"]
        user_id = callback["from"]["id"]
        chat_id = callback["message"]["chat"]["id"]

        telegram(
            "answerCallbackQuery",
            {
                "callback_query_id": callback_id,
                "text": "🔎 در حال بررسی عضویت..."
            }
        )

        # بررسی عضویت
        if is_member(user_id):

            send_message(
                chat_id,
                "✅ عضویتت تأیید شد!\n\n"
                "🎬 تست با موفقیت انجام شد.\n\n"
                "در مرحله بعد سیستم فایل و K-Code را اضافه می‌کنیم."
            )

        else:

            channel_username = CHANNEL.lstrip("@")

            keyboard = [
                [
                    {
                        "text": "📢 عضویت در کانال",
                        "url": f"https://t.me/{channel_username}"
                    }
                ],
                [
                    {
                        "text": "🔄 بررسی مجدد",
                        "callback_data": "check_membership"
                    }
                ]
            ]

            send_message(
                chat_id,
                "❌ هنوز عضویتت تأیید نشده.\n\n"
                "اول عضو کانال شو و بعد دوباره روی "
                "«بررسی مجدد» بزن.",
                keyboard
            )


# =========================
# Health Check
# =========================

@app.route("/", methods=["GET"])
def home():

    return "PandaCityBot is running!", 200


# =========================
# Telegram Webhook
# =========================

@app.route("/telegram", methods=["POST"])
def telegram_webhook():

    update = request.get_json(silent=True)

    if not update:
        return "OK", 200

    try:
        handle_update(update)

    except Exception as error:

        logger.exception(
            "Error while processing update: %s",
            error
        )

    return "OK", 200


# =========================
# ثبت Webhook
# =========================

def setup_webhook():

    webhook_url = f"{RENDER_URL}/telegram"

    result = telegram(
        "setWebhook",
        {
            "url": webhook_url,
            "allowed_updates": [
                "message",
                "callback_query"
            ]
        }
    )

    if result.get("ok"):

        logger.info(
            "Webhook successfully configured: %s",
            webhook_url
        )

    else:

        logger.error(
            "Webhook configuration failed: %s",
            result
        )


# =========================
# اجرای برنامه
# =========================

setup_webhook()
