from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Osnova Coffee Bot is running!"
