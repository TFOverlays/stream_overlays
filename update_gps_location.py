import serial
import pynmea2
import json
import time
import requests

# Replace with your actual GPS device path
PORT = '/dev/tty.usbserial-1130'
ser = serial.Serial(PORT, baudrate=4800, timeout=1)

# Firebase Realtime Database endpoint
FIREBASE_URL = 'https://tfoverlays-default-rtdb.firebaseio.com/location.json'

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

def update_firebase(lat, lon):
    location = reverse_geocode(lat, lon)
    data = {
        'lat': lat,
        'lon': lon,
        'location': location,
        'timestamp': int(time.time())
    }
    try:
        response = requests.patch(FIREBASE_URL, json=data, timeout=5)
        print(f"Pushed to Firebase: {lat}, {lon} -> {location} | Status: {response.status_code}")
    except Exception as e:
        print("Firebase update error:", e)

while True:
    try:
        line = ser.readline().decode('ascii', errors='replace')
        if line.startswith('$GPGGA'):
            msg = pynmea2.parse(line)
            if msg.gps_qual in [1, 2]:  # Only update if valid GPS fix
                lat = round(msg.latitude, 5)
                lon = round(msg.longitude, 5)

                if (lat, lon) != prev_coords:
                    update_firebase(lat, lon)
                    prev_coords = (lat, lon)
                else:
                    print(f"No movement: {lat}, {lon}")
                time.sleep(10)
    except Exception as e:
        print("Error:", e)
        time.sleep(10)
