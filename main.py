import os
import json
from datetime import datetime

import gspread
from flask import Flask, request
import requests
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

BOT_TOKEN = os.environ["8834190639:AAEP-bz8ir3J5i3qcGG2qbPUu9BBeHqmLfY"]
SPREADSHEET_ID = os.environ["1Opeo-CIWDs4Of3MiJb4UBav-GVmnXmsJBy61QV59Zls"]
GOOGLE_CLIENT_EMAIL = os.environ["osnova-bot@osnova-coffee-bot.iam.gserviceaccount.com"]
GOOGLE_PRIVATE_KEY = os.environ["MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC944TvTOaAkVPQ\nwakIMX1l8kvZWzZQpx+fYgbqblNLeUwGZCZrmlxHa4HC4b7Ld21En8HikCdvYLaS\nx7neAsbPQwuOOdG7uIJvwrVfADGDNa2mLuDHEd1D1WV4fe506m/f4rt23rYuxluT\npHT4HVojbK8DWWzMBptW8I8BGX0Z/mK9Pi3sbIc05L2U5eA9pzGSJEq7lbYhTEUG\nmXFasDo3KFsbhJ+Sq3D/7kYDrY8ABK3LNjv2stOJ+NXwISRJ5okxN3uL9qPlbfDB\nNS4an75jAiMqHtYGG6W2+dV4JNQaotntfTpLmnm5yow7kl9FCjN41Oe6nb+m6JqW\nktGjVNwvAgMBAAECggEAGZI9kSI4ekDX2ilyM13CxstJxpP/bP4MhqCjUMeZpPTJ\nNaUf/WaUnbOPDmjrEihbiR3AdNu3y8po27xUvd5+2mNrd3Q218JBon5EgW4bvNEq\nONJgR76SnvNqTj8bMRhvB2XXm+ri+sqQg4HmlJETVejpapiMy67qFVugzmOZ0rmR\nIeIfT3wUKR8KslaBEY2zvTr80wvSOgcKyYbjiNwguoWbREHh5C8CYPF80xlB9LI4\ncaoYI1KLFLGAhogrILOOua0c/ctNz9Cqgog/WyTvZVCUblRxRUI6eLTnK1Zu4cVr\nUxJN78zXkQOPXwIbChxzq/AYMvkVgX38wiKf7b1zsQKBgQDqLLAoCrYcubKWgekO\nWpx+WYHlHXMoJu9+W8RpSRoc1GoWFQX8r6z1+ncIS1SW1lhMYzs6dRriKYjeIa84\nqEPG1JmLdXmRRCXZl7smrU8fGhZPVwRDrS9uZUKr5CXZjhyaSdu1S/Kh9O0l7yxj\naC1ec58AGCRqfVWqcGlCJFKRcQKBgQDPljBw9RekiFvxOfeLGA74WLWZD3Xl2891\nw+OToMJvSEARItR+BF6MqK0+fH1QOpu2ROGO36Dk8L57sxm0uaXomb0zzpnb57X8\n7x82N9yBsMujH+6flUk4SvXkscEK7o8QW7gdmcaFfsfWGna4K0D/w+Eg2UYxtrxs\n1NwJsQF3nwKBgQCJeGx9RTR9joIJmv/+3jCqd88qemxk8N59dk/KYxDCRex1RCg8\nm8DUshF4vAhPeEtjpIlbmu2KQUnI5Utg3l7TdXEiDnesUK5Lm6hRX0Johr78GqA1\nPpDupOFL2WZi3etqo9soBgrNCuTA9TRAsyKXJRb9Ti7qmONWaCFSo9IY8QKBgASn\nLCzMAZyphc4Ra5ANmQBOFLv6kbz2QV81ZduARftyliUML9EnTes/OKrm5XQv7B+Y\nyamHL7cSAmMJb7ESXDqrf4cywVYhin3B6mQvulyZ1uawJ4wiL4L4gyx+I4KYOFK4\ni5b2RHHnlpkg/LpCFfHltR0kYaNpoi2aU9hPxGWnAoGBAMcErovlyVnq8AODjtnH\nO7BsDkVVifxJ0b9qGjYT1o3Ic+XTdgQWo42mwXg3VR6KJ+oIDdCg++Pg/pg3Cz3Y\nZyd1uzteV019rS32mdgPex/RrM6gI6bgb5rL9kiRB7mk2/GhoT6lzGe2dE56AVFp\nygcpeig36XsnX+9D71Ly1jZr"].replace("\\n", "\n")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
REQUIRED_COFFEES = 6

USERS_SHEET = "USERS"
HISTORY_SHEET = "История транзакций"


def get_sheet():
    credentials_dict = {
        "type": "service_account",
        "project_id": "osnova-coffee-bot",
        "private_key": GOOGLE_PRIVATE_KEY,
        "client_email": GOOGLE_CLIENT_EMAIL,
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        credentials_dict,
        scope
    )

    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID)


def send_message(chat_id, text):
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📊 Мій баланс", "callback_data": "BALANCE"},
                {"text": "💳 Моя карта", "callback_data": "CARD"},
            ],
            [
                {"text": "🎁 Як отримати подарунок", "callback_data": "GIFT"},
            ],
        ]
    }

    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "reply_markup": keyboard,
        },
        timeout=10,
    )


def answer_callback(callback_query_id):
    requests.post(
        f"{TELEGRAM_API}/answerCallbackQuery",
        json={"callback_query_id": callback_query_id},
        timeout=10,
    )


def find_user_row(users_sheet, telegram_id):
    rows = users_sheet.get_all_values()

    for index, row in enumerate(rows, start=1):
        if len(row) > 0 and str(row[0]) == str(telegram_id):
            return index, row

    return None, None


def register_user(telegram_id, name):
    spreadsheet = get_sheet()
    users_sheet = spreadsheet.worksheet(USERS_SHEET)

    row_index, _ = find_user_row(users_sheet, telegram_id)

    if row_index is None:
        users_sheet.append_row([
            str(telegram_id),
            name,
            "",
            0,
            0,
            datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        ])


def get_balance(telegram_id):
    spreadsheet = get_sheet()
    users_sheet = spreadsheet.worksheet(USERS_SHEET)

    _, row = find_user_row(users_sheet, telegram_id)

    if not row:
        return 0

    if len(row) < 5:
        return 0

    try:
        return int(row[4])
    except:
        return 0


def log_transaction(telegram_id, name, action):
    try:
        spreadsheet = get_sheet()
        history_sheet = spreadsheet.worksheet(HISTORY_SHEET)

        history_sheet.append_row([
            datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            str(telegram_id),
            name,
            action,
        ])
    except:
        pass


@app.route("/")
def home():
    return "Osnova Coffee Bot is running!"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    if "message" in data:
        message = data["message"]
        text = message.get("text", "")
        user = message["from"]
        chat_id = message["chat"]["id"]

        telegram_id = str(user["id"])
        name = user.get("first_name", "")

        if text.startswith("/start"):
            register_user(telegram_id, name)
            log_transaction(telegram_id, name, "Реєстрація")

            send_message(
                chat_id,
                "☕ Привіт! Ти у програмі лояльності Osnova Bar.\n\n"
                "Кожна 7-а кава — безкоштовно 🎁"
            )
        else:
            send_message(chat_id, "Використовуйте кнопки нижче 👇")

    if "callback_query" in data:
        query = data["callback_query"]
        command = query["data"]
        user = query["from"]
        chat_id = query["message"]["chat"]["id"]

        telegram_id = str(user["id"])
        name = user.get("first_name", "")

        answer_callback(query["id"])

        if command == "BALANCE":
            balance = get_balance(telegram_id)
            remaining = REQUIRED_COFFEES - balance

            send_message(
                chat_id,
                f"☕ Ваш баланс: {balance}/{REQUIRED_COFFEES}\n"
                f"До подарунка залишилось: {remaining} кав"
            )

        elif command == "CARD":
            send_message(
                chat_id,
                "💳 Карта лояльності Osnova Bar\n\n"
                f"Ваш номер карти:\n{telegram_id}\n\n"
                "Покажіть цей номер бариста."
            )

        elif command == "GIFT":
            send_message(
                chat_id,
                "🎁 Збирайте 6 штампів, і 7-а кава буде безкоштовною ☕"
            )

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
