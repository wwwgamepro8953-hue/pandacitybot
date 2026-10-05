import os
import requests
from flask import Flask, request

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL = os.environ.get("CHANNEL", "@StoreAgaAli")
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

app = Flask(__name__)

API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def telegram(method, data=None):
    response = requests.post(
        f"{API}/{method}",
        json=data or {},
        timeout=30
    )
    return response.json()


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


def check_membership(user_id):
    result = telegram(
        "getChatMember",
        {
            "chat_id": CHANNEL,
            "user_id": user_id
        }
    )

    if not result.get("ok"):
        return False

    status = result["result"]["status"]

    return status in ["member", "administrator", "creator"]


def handle_update(update):
    # پیام /start
    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        if text.startswith("/start"):
            send_message(
                chat_id,
                "🐼 سلام! برای دریافت محتوا اول عضو کانال زیر شو 👇",
                [
                    [
                        {
                            "text": "📢 عضویت در کانال",
                            "url": f"https://t.me/{CHANNEL.lstrip('@')}"
                        }
                    ],
                    [
                        {
                            "text": "✅ بررسی عضویت",
                            "callback_data": "check"
                        }
                    ]
                ]
            )

    # دکمه بررسی عضویت
    if "callback_query" in update:
        callback = update["callback_query"]
        user_id = callback["from"]["id"]
        chat_id = callback["message"]["chat"]["id"]

        telegram(
            "answerCallbackQuery",
            {
                "callback_query_id": callback["id"],
                "text": "در حال بررسی..."
            }
        )

        if check_membership(user_id):
            send_message(
                chat_id,
                "✅ عضویتت تأیید شد!\n\n🎬 فعلاً تست موفق بود.\n\nمرحله بعدی ارسال فایل واقعی است."
            )
        else:
            send_message(
                chat_id,
                "❌ هنوز عضو کانال نیستی.\n\nاول عضو شو و دوباره روی «بررسی عضویت» بزن.",
                [
                    [
                        {
                            "text": "📢 عضویت در کانال",
                            "url": f"https://t.me/{CHANNEL.lstrip('@')}"
                        }
                    ],
                    [
                        {
                            "text": "🔄 بررسی مجدد",
                            "callback_data": "check"
                        }
                    ]
                ]
            )


@app.route("/")
def home():
    return "PandaCityBot is running!"


@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    update = request.get_json(silent=True)

    if update:
        handle_update(update)

    return "OK"


if __name__ == "__main__":
    # ثبت Webhook
    telegram(
        "setWebhook",
        {
            "url": f"{WEBHOOK_URL}/telegram"
        }
    )

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
