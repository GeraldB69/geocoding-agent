import requests
import re

def geocode(address):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    }
    headers = {"User-Agent": "AddressSearchAgent/1.0"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data[0] if data else None
    except requests.exceptions.RequestException as e:
        print(f"API error: {e}")
        return None

def reverse_geocode(lat, lon):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": 1,
    }
    headers = {"User-Agent": "AddressSearchAgent/1.0"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data if "lat" in data else None
    except requests.exceptions.RequestException as e:
        print(f"API error: {e}")
        return None

def is_coordinates(text):
    pattern = re.compile(r"^\s*([-+]?\d+\.?\d*)\s*[,;\s]\s*([-+]?\d+\.?\d*)\s*$")
    return pattern.match(text) is not None

def parse_coordinates(text):
    pattern = re.compile(r"^\s*([-+]?\d+\.?\d*)\s*[,;\s]\s*([-+]?\d+\.?\d*)\s*$")
    match = pattern.match(text)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None

def main():
    print("Address & reverse geocoding agent. Type 'quit' to exit.")
    print("You can enter an address or coordinates (e.g., 48.8566, 2.3522).")
    while True:
        user_input = input("\nEnter address or coordinates: ").strip()
        if user_input.lower() in ("quit", "q"):
            print("Goodbye.")
            break
        if not user_input:
            continue

        if is_coordinates(user_input):
            lat, lon = parse_coordinates(user_input)
            if lat is None or lon is None:
                print("Invalid coordinates format.")
                continue
            print(f"Reverse geocoding for {lat}, {lon}...")
            result = reverse_geocode(lat, lon)
            if result:
                print(f"Address: {result.get('display_name')}")
            else:
                print("No address found for these coordinates.")
        else:
            result = geocode(user_input)
            if result:
                print(f"Display name: {result.get('display_name')}")
                print(f"Latitude: {result['lat']}, Longitude: {result['lon']}")
            else:
                print("No result found.")

if __name__ == "__main__":
    main()
