import requests
import sqlite3
import time
from flask import Flask, jsonify, send_file, send_from_directory
import matplotlib.pyplot as plt
import os

# Flask App Initialization
app = Flask(__name__)

# Hypixel API Key (Replace with your actual key)
API_KEY = "5caed84f-3b48-4506-9f78-35548161a8dc"
BAZAAR_URL = "https://api.hypixel.net/skyblock/bazaar"

# Connect to SQLite database
db_conn = sqlite3.connect("app/database.db", check_same_thread=False)
cursor = db_conn.cursor()

# Create table for Bazaar data
cursor.execute("""
    CREATE TABLE IF NOT EXISTS bazaar_prices (
        item_id TEXT PRIMARY KEY,
        sell_price REAL,
        buy_price REAL,
        timestamp INTEGER
    )
""")
db_conn.commit()

# Function to fetch Bazaar data
def fetch_bazaar_data():
    response = requests.get(f"{BAZAAR_URL}?key={API_KEY}")
    return response.json() if response.status_code == 200 else None

# Store Bazaar Data in Database
def store_bazaar_data():
    data = fetch_bazaar_data()
    if data and data.get("success", False):
        timestamp = int(time.time())
        for item_id, item_data in data['products'].items():
            sell_price = item_data['quick_status']['sellPrice']
            buy_price = item_data['quick_status']['buyPrice']

            cursor.execute("""
                INSERT INTO bazaar_prices (item_id, sell_price, buy_price, timestamp)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET 
                    sell_price = excluded.sell_price,
                    buy_price = excluded.buy_price,
                    timestamp = excluded.timestamp
            """, (item_id, sell_price, buy_price, timestamp))

        db_conn.commit()
        print("Bazaar data updated successfully!")
    else:
        print("Failed to fetch Bazaar data.")

# Flask API Endpoint
@app.route('/api/bazaar', methods=['GET'])
def get_bazaar_data():
    cursor.execute("SELECT * FROM bazaar_prices")
    data = cursor.fetchall()
    return jsonify({"data": data})


@app.route('/track')
def track_market():
    """Serves the tracking page for Stock of Stonks & Booster Cookies"""

    return send_from_directory(os.path.join(os.getcwd(), "app/static"), "market_tracking.html")


@app.route('/api/track_items', methods=['GET'])
def get_tracked_items():
    """Fetches historical price data for Stock of Stonks & Booster Cookies"""

    cursor.execute("""
        SELECT item_id, sell_price, timestamp FROM bazaar_prices
        WHERE item_id IN ('STOCK_OF_STONKS', 'BOOSTER_COOKIE')
        ORDER BY timestamp ASC
    """)
    data = cursor.fetchall()
    # Convert data into a dictionary format
    formatted_data = {}
    for item_id, price, timestamp in data:
        if item_id not in formatted_data:
            formatted_data[item_id] = {"timestamps": [], "prices": []}
        formatted_data[item_id]["timestamps"].append(timestamp)
        formatted_data[item_id]["prices"].append(price)

    return jsonify(formatted_data)



# Inflation & Market Trends Analysis
def analyze_market_trends():
    key_items = ["BOOSTER_COOKIE", "STOCK_OF_STONKS"]
    cursor.execute("SELECT item_id, sell_price, timestamp FROM bazaar_prices")
    data = cursor.fetchall()

    # Convert timestamps to readable format
    timestamps = [time.strftime('%Y-%m-%d %H:%M', time.localtime(row[2])) for row in data]
    item_prices = {}

    for row in data:
        item_id, sell_price, timestamp = row
        if item_id in key_items:
            if item_id not in item_prices:
                item_prices[item_id] = []
            item_prices[item_id].append((timestamp, sell_price))

    plt.figure(figsize=(10, 5))
    for item in key_items:
        if item in item_prices:
            timestamps = [x[0] for x in item_prices[item]]
            prices = [x[1] for x in item_prices[item]]
            plt.plot(timestamps, prices, label=item)

    plt.xlabel("Time")
    plt.ylabel("Price (Coins)")
    plt.title("Hypixel Skyblock Market Trends")
    plt.legend()
    plt.savefig("app/static/market_chart.png")  # Save chart for web use
    plt.close()

# Flask Route to Serve Graph
@app.route('/chart')
def serve_chart():
    analyze_market_trends()
    return send_file("app/static/market_chart.png", mimetype='image/png')


@app.route('/')
def home():
    return "Hypixel Economy Tracker is Running!"


# Run Flask App
if __name__ == '__main__':
    store_bazaar_data()
    app.run(debug=True, port=5000)
