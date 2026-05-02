import requests

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

def main():
    print("Address search agent. Type 'quit' or 'q' to exit.")
    while True:
        user_input = input("\nEnter address: ").strip()
        if user_input.lower() in ("quit", "q"):
            print("Goodbye.")
            break
        if not user_input:
            continue

        result = geocode(user_input)
        if result:
            print(f"Display name: {result.get('display_name')}")
            print(f"Latitude: {result['lat']}, Longitude: {result['lon']}")
        else:
            print("No result found.")

if __name__ == "__main__":
    main()