import serial
import pynmea2
import json
import time
import subprocess
import requests

# Replace with your actual GPS device path
PORT = '/dev/tty.usbserial-130'  # e.g., '/dev/tty.usbserial-1410'
ser = serial.Serial(PORT, baudrate=4800, timeout=1)

prev_coords = None

def reverse_geocode(lat, lon):
    try:
        url = 'https://nominatim.openstreetmap.org/reverse'
        params = {
            'format': 'json',
            'lat': lat,
            'lon': lon,
            'zoom': 10,
            'addressdetails': 1
        }
        headers = {
            'User-Agent': 'TwisterFistersOverlay/1.0'
        }
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()
        city = data['address'].get('city') or \
               data['address'].get('town') or \
               data['address'].get('village') or \
               data['address'].get('county') or \
               'Unknown'
        state = data['address'].get('state', '')
        return f"{city}, {state}".strip(", ")
    except Exception as e:
        print("Reverse geocode error:", e)
        return "Unknown"

def update_json(lat, lon):
    location = reverse_geocode(lat, lon)
    with open('location.json', 'w') as f:
        json.dump({'lat': lat, 'lon': lon, 'location': location}, f)

def git_push():
    subprocess.run(["git", "add", "location.json"])
    subprocess.run(["git", "commit", "--amend", "--no-edit"])
    subprocess.run(["git", "push", "--force"])

while True:
    try:
        line = ser.readline().decode('ascii', errors='replace')
        if line.startswith('$GPGGA'):
            msg = pynmea2.parse(line)
            if msg.gps_qual in [1, 2]:  # Only update if valid GPS fix
                lat = msg.latitude
                lon = msg.longitude

                if (lat, lon) != prev_coords:
                    update_json(lat, lon)
                    git_push()
                    print(f"Pushed: {lat}, {lon}")
                    prev_coords = (lat, lon)
                else:
                    print(f"No movement: {lat}, {lon}")
                time.sleep(60)
    except Exception as e:
        print("Error:", e)
        time.sleep(10)
