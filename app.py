from flask import Flask, render_template, request, jsonify
import requests
import sqlite3
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import time  # Not used, but if needed for timestamps

app = Flask(__name__)

# API Key and Base URL for OpenWeatherMap
API_KEY = "8ebd10ad04f96444e9024741ec50b1b2"
BASE_URL = "http://api.openweathermap.org/data/2.5/"

# SQLite database file
SAVED_CITIES_FILE = "saved_cities.db"

def init_db():
    conn = sqlite3.connect(SAVED_CITIES_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cities
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
    conn.commit()
    conn.close()

def load_saved_cities():
    conn = sqlite3.connect(SAVED_CITIES_FILE)
    c = conn.cursor()
    c.execute("SELECT name FROM cities")
    cities = [row[0] for row in c.fetchall()]
    conn.close()
    return cities

def save_city(city):
    conn = sqlite3.connect(SAVED_CITIES_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO cities (name) VALUES (?)", (city,))
    conn.commit()
    conn.close()

def get_weather(city):
    try:
        response = requests.get(f"{BASE_URL}weather?q={city}&appid={API_KEY}&units=metric")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

def get_forecast(city):
    try:
        response = requests.get(f"{BASE_URL}forecast?q={city}&appid={API_KEY}&units=metric")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

def get_air_pollution(lat, lon):
    try:
        response = requests.get(f"{BASE_URL}air_pollution?lat={lat}&lon={lon}&appid={API_KEY}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

def celsius_to_fahrenheit(celsius):
    return celsius * 9/5 + 32

def generate_forecast_graph(city):
    forecast_data = get_forecast(city)
    if not forecast_data or "list" not in forecast_data:
        return None

    # Extract 3-hour forecast data points
    timestamps = [entry["dt_txt"] for entry in forecast_data["list"]]
    temps_c = [entry["main"]["temp"] for entry in forecast_data["list"]]
    temps_f = [celsius_to_fahrenheit(t) for t in temps_c]
    hums = [entry["main"]["humidity"] for entry in forecast_data["list"]]
    rains = [entry.get("rain", {}).get("3h", 0) for entry in forecast_data["list"]]
    snows = [entry.get("snow", {}).get("3h", 0) for entry in forecast_data["list"]]

    # Create 4 subplots
    fig, axs = plt.subplots(4, 1, figsize=(14, 18), sharex=True)

    # Temperature subplot
    axs[0].plot(timestamps, temps_f, marker="o", color="red")
    axs[0].set_ylabel("Temp (°F)")
    axs[0].set_title(f"5-Day Forecast for {city} (3-hour increments)")
    for i, val in enumerate(temps_f):
        axs[0].annotate(f"{val:.1f}", (timestamps[i], temps_f[i]), textcoords="offset points", xytext=(0,5), ha='center', fontsize=8)

    # Humidity subplot
    axs[1].plot(timestamps, hums, marker="x", color="blue")
    axs[1].set_ylabel("Humidity (%)")
    for i, val in enumerate(hums):
        axs[1].annotate(f"{val}%", (timestamps[i], hums[i]), textcoords="offset points", xytext=(0,5), ha='center', fontsize=8)

    # Rain subplot
    axs[2].plot(timestamps, rains, marker="s", color="cyan")
    axs[2].set_ylabel("Rain (mm)")
    for i, val in enumerate(rains):
        axs[2].annotate(f"{val:.1f}", (timestamps[i], rains[i]), textcoords="offset points", xytext=(0,5), ha='center', fontsize=8)

    # Snow subplot
    axs[3].plot(timestamps, snows, marker="^", color="purple")
    axs[3].set_ylabel("Snow (mm)")
    axs[3].set_xlabel("Date & Time")
    for i, val in enumerate(snows):
        axs[3].annotate(f"{val:.1f}", (timestamps[i], snows[i]), textcoords="offset points", xytext=(0,5), ha='center', fontsize=8)

    plt.xticks(rotation=45, fontsize=8)
    plt.tight_layout()

    # Save to BytesIO and encode to base64
    buf = BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    plt.close(fig)  # Close the figure to free memory
    return base64.b64encode(buf.getvalue()).decode('utf-8')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/weather', methods=['GET'])
def api_weather():
    city = request.args.get('city')
    if not city:
        return jsonify({'error': 'City is required'}), 400

    weather_data = get_weather(city)
    if weather_data:
        lat = weather_data['coord']['lat']
        lon = weather_data['coord']['lon']
        air_data = get_air_pollution(lat, lon)
        forecast_graph = generate_forecast_graph(city)

        temp_c = weather_data['main']['temp']
        feels_c = weather_data['main']['feels_like']
        temp_f = celsius_to_fahrenheit(temp_c)
        feels_f = celsius_to_fahrenheit(feels_c)
        description = weather_data['weather'][0]['description'].capitalize()
        humidity = weather_data['main']['humidity']
        wind_speed = weather_data['wind']['speed']

        aqi = air_data["list"][0]["main"]["aqi"] if air_data else 0
        aqi_levels = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}
        aqi_level = aqi_levels.get(aqi, 'Unknown')

        save_city(city)

        return jsonify({
            'weather': {
                'name': weather_data['name'],
                'temp_c': temp_c,
                'temp_f': temp_f,
                'feels_c': feels_c,
                'feels_f': feels_f,
                'description': description,
                'humidity': humidity,
                'wind_speed': wind_speed,
                'lat': lat,
                'lon': lon
            },
            'aqi': {
                'aqi': aqi,
                'level': aqi_level
            },
            'forecast_graph': forecast_graph
        })
    else:
        return jsonify({'error': 'No weather data available'}), 404

@app.route('/api/cities', methods=['GET'])
def api_cities():
    return jsonify(load_saved_cities())

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)