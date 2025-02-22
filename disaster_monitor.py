from flask import Flask, render_template_string, jsonify
import requests
import threading
import time

app = Flask(__name__)

USGS_EARTHQUAKE_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
NWS_ALERTS_URL = "https://api.weather.gov/alerts/active?area=TN"
USGS_WATER_DATA_URL = "https://waterservices.usgs.gov/nwis/iv/?format=json&sites=07022000&parameterCd=00065,00060"

latest_data = {"earthquakes": [], "weather_alerts": [], "flood_data": {}}

def fetch_data(url, key, transform_func):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        latest_data[key] = transform_func(response.json())
    except Exception as e:
        latest_data[key] = [] if isinstance(latest_data[key], list) else {}
        print(f"Error fetching {key} data: {e}")

def parse_earthquake_data(json_data):
    return [
        {"mag": quake["properties"]["mag"], "place": quake["properties"]["place"]}
        for quake in json_data.get("features", []) if quake["properties"]["mag"] >= 1.0
    ]

def parse_weather_alerts(json_data):
    return [
        {"title": alert["properties"]["headline"], "desc": alert["properties"]["description"][:100] + "..."}
        for alert in json_data.get("features", [])
    ]

def parse_flood_data(json_data):
    try:
        time_series = json_data['value']['timeSeries']
        return {
            "discharge": time_series[0]['values'][0]['value'][0]['value'],
            "gage_height": time_series[1]['values'][0]['value'][0]['value']
        }
    except (KeyError, IndexError):
        return {"discharge": "N/A", "gage_height": "N/A"}

def monitor_data():
    while True:
        fetch_data(USGS_EARTHQUAKE_URL, "earthquakes", parse_earthquake_data)
        fetch_data(NWS_ALERTS_URL, "weather_alerts", parse_weather_alerts)
        fetch_data(USGS_WATER_DATA_URL, "flood_data", parse_flood_data)
        time.sleep(600)

@app.route("/api/data")
def api_data():
    return jsonify(latest_data)

@app.route("/")
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Disaster Monitor</title>
        <style>
            body {font-family: Arial; margin: 20px;}
            .section {margin-bottom: 30px;}
            .refresh-btn {padding: 10px 20px; font-size: 16px; cursor: pointer;}
        </style>
        <script>
            async function refreshData() {
                try {
                    const response = await fetch('/api/data');
                    const data = await response.json();
                    document.getElementById('earthquake-section').innerHTML = data.earthquakes.length
                        ? '<ul>' + data.earthquakes.map(q => `<li>Magnitude ${q.mag} near ${q.place}</li>`).join('') + '</ul>'
                        : '<p>No recent earthquakes.</p>';

                    document.getElementById('weather-section').innerHTML = data.weather_alerts.length
                        ? '<ul>' + data.weather_alerts.map(a => `<li><b>${a.title}</b>: ${a.desc}</li>`).join('') + '</ul>'
                        : '<p>No active weather alerts.</p>';

                    document.getElementById('flood-section').innerText = `Stream Discharge: ${data.flood_data.discharge} cfs | Gage Height: ${data.flood_data.gage_height} ft`;
                } catch (error) {
                    console.error('Error refreshing data:', error);
                }
            }
            window.onload = refreshData;
        </script>
    </head>
    <body>
        <h1>🌐 Disaster Monitor by Noah Shipley</h1>
        <h2>Currently broadcasts only regions from the United States.</h2>
        <button class="refresh-btn" onclick="refreshData()">🔄 Refresh Data</button>
        <div class="section" id="earthquake-section"><p>Loading earthquake data...</p></div>
        <div class="section" id="weather-section"><p>Loading weather alerts...</p></div>
        <div class="section" id="flood-section"><p>Loading flood data...</p></div>
    </body>
    <footer>Owned by The Caldera.</footer>
    </html>
    """)

if __name__ == "__main__":
    threading.Thread(target=monitor_data, daemon=True).start()
    app.run(debug=True, host='0.0.0.0', port=5000)
