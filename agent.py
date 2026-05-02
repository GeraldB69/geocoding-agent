import requests

TEST_ADDRESS = "1 rue de la Paix, Paris"

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
    print(f"Searching for: {TEST_ADDRESS}")
    result = geocode(TEST_ADDRESS)

    if result:
        print("Address found:")
        print(f"  Display name: {result.get('display_name')}")
        print(f"  Latitude: {result['lat']}")
        print(f"  Longitude: {result['lon']}")
    else:
        print("No result found.")

if __name__ == "__main__":
    main()
