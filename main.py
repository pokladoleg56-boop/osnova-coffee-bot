import os
import json
from datetime import datetime

import gspread
from flask import Flask, request
import requests
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]
GOOGLE_CLIENT_EMAIL = os.environ["GOOGLE_CLIENT_EMAIL"]
GOOGLE_PRIVATE_KEY = os.environ["GOOGLE_PRIVATE_KEY"].replace("\\n", "\n")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
REQUIRED_COFFEES = 6

USERS_SHEET = "USERS"
HISTORY_SHEET = "История транзакций"


def get_sheet():
    credentials_dict = {
    "type": "service_account",
    "project_id": "osnova-coffee-bot",
    "private_key_id": os.environ["GOOGLE_PRIVATE_KEY_ID"],
    "private_key": GOOGLE_PRIVATE_KEY,
    "client_email": GOOGLE_CLIENT_EMAIL,
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
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
