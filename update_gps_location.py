import serial
import pynmea2
import json
import time
import requests

# GPS device path and Firebase URL
PORT = '/dev/tty.usbserial-1130'
BAUDRATE = 4800
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

def push_to_firebase(lat, lon, location):
    payload = {
        'lat': lat,
        'lon': lon,
        'location': location
    }
    try:
        response = requests.put(FIREBASE_URL, json=payload)
        if response.status_code == 200:
            print(f"Pushed to Firebase: {lat}, {lon} - {location}")
        else:
            print(f"Failed to push: {response.status_code} - {response.text}")
    except Exception as e:
        print("Firebase push error:", e)

while True:
    try:
        # Re-open the serial port fresh each cycle
        with serial.Serial(PORT, baudrate=BAUDRATE, timeout=1) as ser:
            # Give it a short window to try reading a fix
            start_time = time.time()
            while time.time() - start_time < 5:
                line = ser.readline().decode('ascii', errors='replace')
                if line.startswith('$GPGGA'):
                    msg = pynmea2.parse(line)
                    if msg.gps_qual in [1, 2]:
                        lat = round(msg.latitude, 5)
                        lon = round(msg.longitude, 5)

                        if (lat, lon) != prev_coords:
                            location = reverse_geocode(lat, lon)
                            push_to_firebase(lat, lon, location)
                            prev_coords = (lat, lon)
                        else:
                            print(f"No movement: {lat}, {lon}")
                        break  # Exit loop once a valid fix is handled
        time.sleep(10)
    except Exception as e:
        print("Error:", e)
        time.sleep(10)
