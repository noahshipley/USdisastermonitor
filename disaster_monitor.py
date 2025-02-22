from flask import Flask, render_template_string
import requests
import threading
import time

app = Flask(__name__)

USGS_EARTHQUAKE_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
NWS_ALERTS_URL = "https://api.weather.gov/alerts/active?area=TN"
USGS_WATER_DATA_URL = "https://waterservices.usgs.gov/nwis/iv/?format=json&sites=07022000&parameterCd=00065,00060"

latest_data = {"earthquakes": [], "weather_alerts": [], "flood_data": {}}

def check_earthquakes():
    try:
        response = requests.get(USGS_EARTHQUAKE_URL)
        earthquakes = response.json().get("features", [])
        latest_data["earthquakes"] = [
            {"mag": quake["properties"]["mag"], "place": quake["properties"]["place"]}
            for quake in earthquakes if quake["properties"]["mag"] >= 1.0
        ]
    except:
        latest_data["earthquakes"] = []

def check_weather_alerts():
    try:
        response = requests.get(NWS_ALERTS_URL)
        alerts = response.json().get("features", [])
        latest_data["weather_alerts"] = [
            {"title": alert["properties"]["headline"], "desc": alert["properties"]["description"][:100] + "..."}
            for alert in alerts
        ]
    except:
        latest_data["weather_alerts"] = []

def check_flood_data():
    try:
        response = requests.get(USGS_WATER_DATA_URL)
        data = response.json()
        discharge = data['value']['timeSeries'][0]['values'][0]['value'][0]['value']
        gage_height = data['value']['timeSeries'][1]['values'][0]['value'][0]['value']
        latest_data["flood_data"] = {"discharge": discharge, "gage_height": gage_height}
    except:
        latest_data["flood_data"] = {"discharge": "N/A", "gage_height": "N/A"}

def monitor_data():
    while True:
        check_earthquakes()
        check_weather_alerts()
        check_flood_data()
        time.sleep(600)

@app.route("/")
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>United States Disaster Monitor</title>
        <style>body {font-family: Arial; margin: 20px;} .section {margin-bottom: 30px;}</style>
    </head>
    <body>
        <h1>🌐 US Disaster Monitor by Noah Shipley on Github</h1>
        <div class="section">
            <h2>🌎 Earthquake Alerts</h2>
            {% if earthquakes %}
                <ul>{% for quake in earthquakes %}<li>Magnitude {{ quake.mag }} near {{ quake.place }}</li>{% endfor %}</ul>
            {% else %}<p>No recent earthquakes.</p>{% endif %}
        </div>
        <div class="section">
            <h2>⛈️ Weather Alerts</h2>
            {% if weather_alerts %}
                <ul>{% for alert in weather_alerts %}<li><b>{{ alert.title }}</b>: {{ alert.desc }}</li>{% endfor %}</ul>
            {% else %}<p>No active weather alerts.</p>{% endif %}
        </div>
        <div class="section">
            <h2>🌊 Flood Data</h2>
            <p>Stream Discharge: {{ flood_data.discharge }} cfs | Gage Height: {{ flood_data.gage_height }} ft</p>
        </div>
    </body>
    </html>
    """, earthquakes=latest_data["earthquakes"], weather_alerts=latest_data["weather_alerts"], flood_data=latest_data["flood_data"])

if __name__ == "__main__":
    threading.Thread(target=monitor_data, daemon=True).start()
    app.run(debug=True, port=5000)
