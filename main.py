import os
import sqlite3
from flask import Flask, request, jsonify, render_template
from datetime import datetime
from binance.client import Client

app = Flask(__name__)

# Load Binance credentials from environment variables
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

# Use the Binance.US base URL
client = Client(API_KEY, API_SECRET, base_url='https://api.binance.us')

# Initialize SQLite DB
DB_FILE = "trades.db"
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            symbol TEXT,
            qty REAL,
            entry_price REAL,
            sl_price REAL,
            tp_price REAL,
            timestamp TEXT,
            status TEXT,
            error TEXT
        )
        """)
init_db()

def log_trade(data):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO trades (action, symbol, qty, entry_price, sl_price, tp_price, timestamp, status, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                data.get("action"),
                data.get("symbol"),
                data.get("qty"),
                data.get("entry_price"),
                data.get("sl_price"),
                data.get("tp_price"),
                datetime.utcnow().isoformat(),
                data.get("status"),
                data.get("error")
            )
        )

@app.route("/")
def index():
    return "Bot is running (Binance.US)"

@app.route("/dashboard")
def dashboard():
    with sqlite3.connect(DB_FILE) as conn:
        trades = conn.execute("SELECT * FROM trades ORDER BY id DESC LIMIT 25").fetchall()
    return render_template("dashboard.html", trades=trades)

@app.route("/logs")
def logs():
    with sqlite3.connect(DB_FILE) as conn:
        logs = conn.execute("SELECT timestamp, action, symbol, status, error FROM trades WHERE status='error' ORDER BY id DESC LIMIT 50").fetchall()
    return render_template("logs.html", logs=logs)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    response = {}
    try:
        action = data.get("action")
        symbol = data.get("symbol")
        qty = float(data.get("qty"))
        entry_price = float(data.get("entry_price", 0))
        sl_price = float(data.get("sl_price", 0))
        tp_price = float(data.get("tp_price", 0))

        if action == "BUY":
            order = client.new_order(symbol=symbol, side="BUY", type="MARKET", quantity=qty)
            response = {"status": "success"}
            data["status"] = "success"
            data["error"] = ""

        elif action == "SELL":
            order = client.new_order(symbol=symbol, side="SELL", type="MARKET", quantity=qty)
            response = {"status": "success"}
            data["status"] = "success"
            data["error"] = ""
        else:
            raise ValueError("Invalid action")

    except Exception as e:
        response = {"error": str(e)}
        data["status"] = "error"
        data["error"] = str(e)

    log_trade(data)
    return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
