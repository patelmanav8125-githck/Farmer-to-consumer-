# 🌾 FarmDirect - Open Farmer-to-Consumer Portal

A modern, open-access agricultural portal connecting farmers directly with consumers, powered by the **Agmarknet Daily Mandi Prices dataset (data.gov.in)** and AI Price Forecasting.

---

## 🚀 Features

- **🔓 100% Open Access**: No login, sign-up, or accounts required for consumers or farmers.
- **📊 AI Price Forecasting**: Real-time price predictions and trend analysis for major Gujarat crops (Tomato, Potato, Onion, Wheat, Rice, Cotton) powered by official **Agmarknet daily APMC mandi data**.
- **🛒 Direct Marketplace**: Consumers can directly order produce from local growers without middleman markups.
- **👨‍🌾 Open Produce Listing**: Any farmer can immediately list their harvest with zero platform fees or barriers.
- **🔍 Instant Live Search & Filtering**: Filter produce in real-time by crop name, farmer name, and categories.

---

## 📁 Project Structure

```
pm GTU/
├── index.html                   # Open-access frontend portal UI
├── style.css                    # Responsive styling & themes
├── app.py                       # Flask backend REST API
├── agmarknet_daily_prices.csv   # 7,600+ Agmarknet daily mandi records
├── farmdirect.db                # SQLite database (Mandi prices, products, orders)
└── generate_agmarknet_data.py   # Dataset generator / refresher script
```

---

## 📊 Dataset: Agmarknet Daily Mandi Prices (`data.gov.in`)

The dataset conforms to the **Directorate of Marketing & Inspection (DMI) / Agmarknet schema**:

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `state` | TEXT | State (Gujarat) |
| `district` | TEXT | District (Ahmedabad, Surat, Rajkot, Vadodara, etc.) |
| `market` | TEXT | APMC Mandi name (e.g., Ahmedabad APMC, Rajkot APMC) |
| `commodity` | TEXT | Crop name (Tomato, Potato, Onion, Wheat, Rice, Cotton) |
| `variety` | TEXT | Crop variety (Anand-3, Kufri Badshah, Sharbati, Shankar-6) |
| `arrival_date` | TEXT | Date of mandi arrival (`YYYY-MM-DD`) |
| `min_price_rs_quintal` | INTEGER | Minimum price recorded in mandi (₹ / quintal) |
| `max_price_rs_quintal` | INTEGER | Maximum price recorded in mandi (₹ / quintal) |
| `modal_price_rs_quintal` | INTEGER | Modal (most frequent) price (₹ / quintal) |
| `modal_price_rs_kg` | REAL | Price per kg (`modal_price / 100`) |
| `arrival_tonnes` | REAL | Total mandi arrival volume in metric tonnes |

---

## 🏃 Quick Start: How to Run

### 1. Run the Backend & Portal
In your terminal, run:

```bash
python3 app.py
```

Open your browser and visit:
👉 **[http://127.0.0.1:5001](http://127.0.0.1:5001)**

The Flask server serves both the **REST API** and the **frontend website**.

*(Note: The frontend also has graceful fallback logic, so if opened standalone via `index.html`, it continues to work smoothly).*

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/forecast?crop=Tomato&market=Ahmedabad&period=15%20Days` | Returns AI price forecast, trend %, and recommendations from Agmarknet data |
| `GET` | `/api/products` | Returns all active marketplace produce listings |
| `POST` | `/api/products` | Open produce listing endpoint for farmers |
| `POST` | `/api/orders` | Open direct purchase endpoint (generates order code, e.g. `FD-39723`) |
| `GET` | `/api/mandi-overview` | Latest summary across all Gujarat APMC mandis |

---

## 🌐 Optional: Connecting Live to `data.gov.in` API

If you register on [data.gov.in](https://data.gov.in) and obtain a free API key:
1. Resource ID: `9ef84268-d588-465a-a308-a864a43d0070`
2. Endpoint:
   ```
   https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key=YOUR_KEY&format=json&filters[state]=Gujarat
   ```
The backend can sync live records directly into `farmdirect.db`.
