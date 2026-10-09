"""
FarmDirect Backend API
Powered by Agmarknet Daily Mandi Prices (data.gov.in)
"""

import os
import sqlite3
import random
import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "farmdirect.db")

app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")
CORS(app)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ----------------- STATIC FRONTEND ROUTES -----------------

@app.route("/")
def serve_index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/<path:path>")
def serve_static(path):
    if os.path.exists(os.path.join(BASE_DIR, path)):
        return send_from_directory(BASE_DIR, path)
    return send_from_directory(BASE_DIR, "index.html")


# ----------------- AGMARKNET FORECAST API -----------------

@app.route("/api/forecast", methods=["GET"])
def get_forecast():
    """
    Computes price forecast using historical Agmarknet daily mandi records.
    Query params:
      - crop (e.g. Tomato, Potato, Onion, Wheat, Rice, Cotton)
      - market (e.g. Ahmedabad, Vadodara, Rajkot, Surat, Junagadh)
      - period (e.g. 7 Days, 15 Days, 30 Days, 3 Months)
    """
    crop = request.args.get("crop", "Tomato").strip()
    market_query = request.args.get("market", "Ahmedabad").strip()
    period = request.args.get("period", "15 Days").strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Query recent 60 days of Agmarknet mandi data for this crop and market
    cursor.execute("""
        SELECT arrival_date, min_price_rs_quintal, max_price_rs_quintal,
               modal_price_rs_quintal, modal_price_rs_kg, arrival_tonnes, variety, market
        FROM mandi_prices
        WHERE commodity LIKE ? AND market LIKE ?
        ORDER BY arrival_date ASC
    """, (f"%{crop}%", f"%{market_query}%"))

    rows = cursor.fetchall()

    # Fallback to any market if specified market has no records
    if not rows:
        cursor.execute("""
            SELECT arrival_date, min_price_rs_quintal, max_price_rs_quintal,
                   modal_price_rs_quintal, modal_price_rs_kg, arrival_tonnes, variety, market
            FROM mandi_prices
            WHERE commodity LIKE ?
            ORDER BY arrival_date ASC
        """, (f"%{crop}%",))
        rows = cursor.fetchall()

    conn.close()

    if not rows:
        return jsonify({
            "status": "error",
            "message": f"No Agmarknet data found for crop: {crop}"
        }), 404

    # Extract historical modal prices
    prices = [r["modal_price_rs_kg"] for r in rows]
    recent_arrivals = [r["arrival_tonnes"] for r in rows[-15:]]
    avg_arrivals = sum(recent_arrivals) / len(recent_arrivals) if recent_arrivals else 100.0

    current_price = prices[-1]
    variety = rows[-1]["variety"]
    market_name = rows[-1]["market"]

    # Calculate recent momentum (last 15 days vs previous 15 days)
    if len(prices) >= 30:
        p_now = sum(prices[-15:]) / 15.0
        p_prev = sum(prices[-30:-15]) / 15.0
        momentum = (p_now - p_prev) / p_prev
    else:
        momentum = 0.05

    # Period factor & duration mapping
    period_days_map = {
        "7 Days": 7,
        "15 Days": 15,
        "30 Days": 30,
        "3 Months": 90
    }
    days = period_days_map.get(period, 15)

    # Seasonal & crop factors
    crop_growth_bias = {
        "Tomato": 0.12,
        "Potato": 0.08,
        "Onion": 0.25,
        "Wheat": 0.05,
        "Rice": 0.04,
        "Cotton": 0.10
    }
    bias = crop_growth_bias.get(crop, 0.06)

    # Calculate forecast
    # Short term follows momentum, medium term factors seasonality and arrival volumes
    arrival_pressure = -0.05 if avg_arrivals > 180 else 0.05
    forecast_ratio = (momentum * (days / 15.0) * 0.4) + (bias * (days / 30.0) * 0.6) + arrival_pressure
    
    # Bound between -20% and +50% for realistic bounds
    forecast_ratio = max(-0.15, min(0.48, forecast_ratio))
    predicted_price = round(current_price * (1.0 + forecast_ratio), 2)
    change_pct = round(forecast_ratio * 100.0, 1)

    trend_sign = "+" if change_pct >= 0 else ""
    trend_str = f"📈 {trend_sign}{change_pct}%" if change_pct >= 0 else f"📉 {change_pct}%"

    # Generate recommendation based on Agmarknet arrivals and price trajectory
    if change_pct > 10:
        rec = f"Prices in {market_name} are expected to rise significantly over the next {period}. Farmers may consider holding stock or selling in batches to maximize returns."
    elif change_pct > 0:
        rec = f"Moderate upward price movement expected over the next {period}. Demand remains steady across Gujarat mandis."
    else:
        rec = f"Arrivals in {market_name} are expected to increase over {period}. Farmers with ready harvest are advised to sell early to lock in current rates."

    # Build 6 trajectory points for the UI chart
    step = (predicted_price - current_price) / 5.0
    chart_points = [
        round(current_price + (step * i), 2) for i in range(6)
    ]

    return jsonify({
        "status": "success",
        "source": "Agmarknet (data.gov.in)",
        "crop": crop,
        "variety": variety,
        "market": market_name,
        "period": period,
        "current_price_kg": current_price,
        "current_price_quintal": round(current_price * 100),
        "predicted_price_kg": predicted_price,
        "predicted_price_quintal": round(predicted_price * 100),
        "trend": trend_str,
        "change_percent": change_pct,
        "avg_daily_arrival_tonnes": round(avg_arrivals, 1),
        "recommendation": rec,
        "chart_points": chart_points
    })


# ----------------- MARKETPLACE PRODUCTS API -----------------

@app.route("/api/products", methods=["GET"])
def get_products():
    """Returns active marketplace products."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, product_name, category, farmer_name, location,
               price_per_kg, farmer_phone, icon, created_at
        FROM marketplace_products
        ORDER BY id ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    products = [dict(r) for r in rows]
    return jsonify({
        "status": "success",
        "count": len(products),
        "products": products
    })

@app.route("/api/products", methods=["POST"])
def add_product():
    """Open listing endpoint for farmers (no login required)."""
    data = request.get_json() or {}
    product_name = data.get("product_name", "").strip()
    category = data.get("category", "Vegetables").strip()
    farmer_name = data.get("farmer_name", "").strip()
    location = data.get("location", "Gujarat").strip()
    price = float(data.get("price_per_kg", 30.0))
    phone = data.get("farmer_phone", "").strip()
    icon = data.get("icon", "🌾").strip()

    if not product_name or not farmer_name:
        return jsonify({"status": "error", "message": "Missing product_name or farmer_name"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO marketplace_products (
            product_name, category, farmer_name, location, price_per_kg, farmer_phone, icon
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (product_name, category, farmer_name, location, price, phone, icon))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Product listed on open marketplace successfully!",
        "product": {
            "id": new_id,
            "product_name": product_name,
            "category": category,
            "farmer_name": farmer_name,
            "location": location,
            "price_per_kg": price,
            "farmer_phone": phone,
            "icon": icon
        }
    }), 201


# ----------------- DIRECT ORDERS API -----------------

@app.route("/api/orders", methods=["POST"])
def create_order():
    """Open direct purchase endpoint (no login required)."""
    data = request.get_json() or {}
    product_name = data.get("product_name", "").strip()
    farmer_name = data.get("farmer_name", "").strip()
    buyer_name = data.get("buyer_name", "").strip()
    buyer_phone = data.get("buyer_phone", "").strip()
    quantity_kg = float(data.get("quantity_kg", 5.0))
    delivery_city = data.get("delivery_city", "").strip()
    notes = data.get("delivery_notes", "").strip()
    total_price = float(data.get("total_price", 0.0))

    if not buyer_name or not buyer_phone:
        return jsonify({"status": "error", "message": "Missing buyer_name or buyer_phone"}), 400

    order_code = f"FD-{random.randint(10000, 99999)}"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO direct_orders (
            order_code, product_name, farmer_name, buyer_name, buyer_phone,
            quantity_kg, delivery_city, delivery_notes, total_price
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (order_code, product_name, farmer_name, buyer_name, buyer_phone,
          quantity_kg, delivery_city, notes, total_price))
    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "order_code": order_code,
        "message": f"Direct order {order_code} confirmed! Connect directly with {farmer_name}."
    }), 201


# ----------------- AGMARKNET OVERVIEW API -----------------

@app.route("/api/mandi-overview", methods=["GET"])
def mandi_overview():
    """Summary of latest Agmarknet modal prices across crops."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT commodity, market, variety, modal_price_rs_kg, modal_price_rs_quintal,
               min_price_rs_quintal, max_price_rs_quintal, arrival_date
        FROM mandi_prices
        WHERE arrival_date = (SELECT MAX(arrival_date) FROM mandi_prices)
        GROUP BY commodity, market
        ORDER BY commodity ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    return jsonify({
        "status": "success",
        "source": "Agmarknet (data.gov.in)",
        "as_of_date": rows[0]["arrival_date"] if rows else "2026-10-07",
        "commodities": [dict(r) for r in rows]
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"🌾 FarmDirect Backend running on http://127.0.0.1:{port}")
    print(f"📊 Connected to Agmarknet dataset ({DB_PATH})")
    app.run(host="0.0.0.0", port=port, debug=True)
