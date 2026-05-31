import os
import json
from datetime import datetime
from urllib.parse import quote

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

BARISTA_IDS = ["128621776"]

def add_coffee_by_bot(client_id, barista_chat_id):
    spreadsheet = get_sheet()
    users_sheet = spreadsheet.worksheet(USERS_SHEET)

    row_index, row = find_user_row(users_sheet, client_id)

    if row_index is None:
        send_message(barista_chat_id, "❌ Клиент не найден")
        return

    name = row[1] if len(row) > 1 else ""
    total = int(row[3]) if len(row) > 3 and row[3] else 0
    balance = int(row[4]) if len(row) > 4 and row[4] else 0

    total += 1
    balance += 1

    if balance >= REQUIRED_COFFEES:
        balance = 0
        result = "🎉 Подарочная кава доступна!"
        client_text = "🎉 Вітаємо! У вас є безкоштовна кава ☕"
    else:
        result = f"Начислено. Баланс: {balance}/{REQUIRED_COFFEES}"
        client_text = f"☕ +1 кава зарахована!\n\nВаш баланс: {balance}/{REQUIRED_COFFEES}"

    users_sheet.update_cell(row_index, 4, total)
    users_sheet.update_cell(row_index, 5, balance)
    users_sheet.update_cell(row_index, 6, datetime.now().strftime("%d.%m.%Y %H:%M:%S"))

    log_transaction(client_id, name, "+1 кава")

    send_message(client_id, client_text)
def send_barista_add_more_buttons(chat_id, client_id, result):
    balance = get_balance(client_id)

    buttons = [
        [
            {"text": "➕ +1", "callback_data": f"ADD_MORE:{client_id}:1"},
            {"text": "➕ +2", "callback_data": f"ADD_MORE:{client_id}:2"},
            {"text": "➕ +3", "callback_data": f"ADD_MORE:{client_id}:3"},
        ]
    ]

    if balance >= REQUIRED_COFFEES:
        buttons.append([
            {"text": "🎁 Списать подарок", "callback_data": f"USE_BONUS:{client_id}"}
        ])

    keyboard = {
        "inline_keyboard": buttons
    }

    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": "✅ " + result + "\n\nДодати ще каву?",
            "reply_markup": keyboard,
        },
        timeout=10,
    )    
def send_qr_card(chat_id, telegram_id):
    bot_username = "Osnovabar_bot"

    add_link = f"https://t.me/{bot_username}?start=add_{telegram_id}"
    qr_url = "https://api.qrserver.com/v1/create-qr-code/?size=500x500&data=" + quote(add_link)
    
    requests.post(
        f"{TELEGRAM_API}/sendPhoto",
        json={
            "chat_id": chat_id,
            "photo": qr_url,
            "caption": (
                "💳 Карта лояльності Osnova Bar\n\n"
                f"Ваш номер карти: {telegram_id}\n\n"
                "Покажіть цей QR бариста для нарахування кави."
            )
        },
        timeout=10,
    )
def send_barista_add_more_buttons(chat_id, client_id, result):
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "➕ +1", "callback_data": f"ADD_MORE:{client_id}:1"},
                {"text": "➕ +2", "callback_data": f"ADD_MORE:{client_id}:2"},
                {"text": "➕ +3", "callback_data": f"ADD_MORE:{client_id}:3"},
            ]
        ]
    }

    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": "✅ " + result + "\n\nДодати ще каву?",
            "reply_markup": keyboard,
        },
        timeout=10,
    )
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    if "callback_query" in data:
        query = data["callback_query"]
        command = query["data"]
        user = query["from"]
        chat_id = query["message"]["chat"]["id"]

        telegram_id = str(user["id"])
        name = user.get("first_name", "")

        answer_callback(query["id"])
        if command.startswith("ADD_MORE:"):
            if telegram_id not in BARISTA_IDS:
                send_message(chat_id, "❌ У вас нет доступа")
                return "ok"

            _, client_id, count_text = command.split(":")
            count = int(count_text)

            for _ in range(count):
                add_coffee_by_bot(client_id, chat_id)

            return "ok"

        if command == "BALANCE":
            balance = get_balance(telegram_id)
            remaining = REQUIRED_COFFEES - balance
            progress = "☕" * balance + "⬜" * remaining

            send_message(
                chat_id,
                "☕ Osnova Bar\n\n"
                f"{progress}\n\n"
                f"Ваш баланс: {balance}/{REQUIRED_COFFEES}\n"
                f"До подарунка залишилось: {remaining} кав"
            )
        if command.startswith("USE_BONUS:"):
            if telegram_id not in BARISTA_IDS:
                send_message(chat_id, "❌ У вас нет доступа")
                return "ok"

            _, client_id = command.split(":")
            use_bonus_coffee(client_id, chat_id)
            return "ok"

        elif command == "CARD":
            send_qr_card(chat_id, telegram_id)

        elif command == "GIFT":
            send_message(
                chat_id,
                "🎁 Збирайте 6 штампів, і 7-а кава буде безкоштовною ☕"
            )

        return "ok"

    if "message" in data:
        message = data["message"]
        text = message.get("text", "")
        user = message["from"]
        chat_id = message["chat"]["id"]

        telegram_id = str(user["id"])
        name = user.get("first_name", "")

        if text.startswith("/add"):
            if telegram_id not in BARISTA_IDS:
                send_message(chat_id, "❌ У вас нет доступа")
                return "ok"

            parts = text.split()

            if len(parts) < 2:
                send_message(chat_id, "Введите так: /add 128621776")
                return "ok"

            client_id = parts[1].strip()
            add_coffee_by_bot(client_id, chat_id)
            return "ok"
        if text.startswith("/start add_"):
            if telegram_id not in BARISTA_IDS:
                send_message(chat_id, "❌ У вас нет доступа для начисления кави")
                return "ok"

            client_id = text.replace("/start add_", "").strip()

            if not client_id:
                send_message(chat_id, "❌ Не найден номер карты")
                return "ok"

            add_coffee_by_bot(client_id, chat_id)
            return "ok"

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

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
