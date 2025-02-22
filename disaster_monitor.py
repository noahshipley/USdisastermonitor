from flask import Flask, render_template_string, jsonify, request
import requests
import threading
import time

app = Flask(__name__)

COUNTRY_DATA_URLS = {
    "US": {
        "earthquake": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson",
        "weather": "https://api.weather.gov/alerts/active",
        "flood": "https://waterservices.usgs.gov/nwis/iv/?format=json&sites=07022000&parameterCd=00065,00060"
    },
    "DE": {
    "earthquake": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson?minlatitude=47.3&maxlatitude=55.3&minlongitude=5.8&maxlongitude=15.0",
    "weather": "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=51.1657&lon=10.4515",
    "flood": "https://api.pegelonline.wsv.de/webservices/rest-api/v2/stations.json"
    },
    "UK": {
        "earthquake": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson?minlatitude=49.5&maxlatitude=60.8&minlongitude=-8.2&maxlongitude=1.8",
        "weather": "https://www.metoffice.gov.uk/public/data/val/wxfcs/all/json/uk",
        "flood": "https://environment.data.gov.uk/flood-monitoring/id/floods"
    },
    "CA": {
    "earthquake": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson?minlatitude=41.7&maxlatitude=83.1&minlongitude=-141.0&maxlongitude=-52.0",
    "weather": "https://api.weather.gc.ca/alerts/index_e.html?area=CA&format=json",
    "flood": "https://dd.weather.gc.ca/hydrometric/data/v1/Station/StationList.json"
    },
    "MX": {
    "earthquake": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson?minlatitude=14.5&maxlatitude=32.7&minlongitude=-118.5&maxlongitude=-86.7",
    "weather": "https://api.openweathermap.org/data/2.5/alerts?lat=23.6345&lon=-102.5528&appid=YOUR_API_KEY",
    "flood": "https://api.gob.mx/floods"
    }
}

latest_data = {country: {"earthquakes": [], "weather_alerts": [], "flood_data": {}} for country in COUNTRY_DATA_URLS}

def fetch_data(url, key, country, transform_func):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        latest_data[country][key] = transform_func(response.json())
    except Exception as e:
        latest_data[country][key] = [] if isinstance(latest_data[country][key], list) else {}
        print(f"Error fetching {key} data for {country}: {e}")

def parse_earthquake_data(json_data):
    return [
        {"mag": quake["properties"]["mag"], "place": quake["properties"]["place"]}
        for quake in json_data.get("features", []) if quake["properties"]["mag"] >= 1.0
    ]

def parse_weather_alerts(json_data):
    return [
        {"title": alert["properties"].get("headline", "No title"), "desc": alert["properties"].get("description", "")[0:100] + "..."}
        for alert in json_data.get("features", [])
    ]

def parse_flood_data(json_data):
    try:
        return {"discharge": json_data["discharge"], "gage_height": json_data["gage_height"]}
    except (KeyError, IndexError):
        return {"discharge": "N/A", "gage_height": "N/A"}

def monitor_data():
    while True:
        for country, urls in COUNTRY_DATA_URLS.items():
            fetch_data(urls["earthquake"], "earthquakes", country, parse_earthquake_data)
            fetch_data(urls["weather"], "weather_alerts", country, parse_weather_alerts)
            fetch_data(urls["flood"], "flood_data", country, parse_flood_data)
        time.sleep(600)

@app.route("/api/data")
def api_data():
    country = request.args.get("country", "US")
    return jsonify(latest_data.get(country, latest_data["US"]))

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
            select {padding: 5px; font-size: 16px;}
        </style>
        <script>
            async function refreshData() {
                const country = document.getElementById('country-select').value;
                try {
                    const response = await fetch(`/api/data?country=${country}`);
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
        <h2>Select a country to view real-time disaster data:</h2>
        <select id="country-select" onchange="refreshData()">
            <option value="US">United States</option>
            <option value="DE">Germany</option>
            <option value="UK">United Kingdom</option>
            <option value="CA">Canada</option>
            <option value="MX">Mexico</option>
        </select>
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
