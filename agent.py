import requests
import re
import json

# Fallback rules (when Ollama is unavailable)

STREET_PATTERN = re.compile(
    r"^\s*(rue|avenue|boulevard|place|allée|chemin|impasse|route|square|cours)\b",
    re.IGNORECASE
)

def is_street_only(query):
    query = query.strip()
    if "," in query:
        return False
    if re.search(r"\d", query):
        return False
    return bool(STREET_PATTERN.match(query))

def has_locality_hint(query):
    query = query.strip()
    if "," in query:
        return True
    if re.search(r"(?<!\d)\d{5}(?!\d)", query):
        return True
    return False

# Ollama integration

def analyze_with_llm(text):
    """Returns a dict with keys: language, precise, message (if not precise).
    Returns None if Ollama is not reachable."""
    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "llama3.1:8b",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an address analysis assistant. Given a user input, determine: "
                            "1. The language of the input (e.g., 'fr', 'en', 'es', 'de'). "
                            "2. Whether the address is precise enough for geocoding. A precise address must include a street (with or without number) AND either a city or a postal code. "
                            "If precise is false, provide a polite message in the detected language asking for the missing information (e.g., 'Please provide a city or postal code.'). "
                            "Respond ONLY with a valid JSON object containing exactly: "
                            "{\"language\": \"xx\", \"precise\": true/false, \"message\": \"...\"}. "
                            "No extra text."
                        )
                    },
                    {"role": "user", "content": text}
                ],
                "stream": False,
                "options": {"temperature": 0}
            },
            timeout=10
        )
        data = response.json()
        content = data["message"]["content"].strip()
        # Extract JSON object (sometimes LLM wraps in backticks)
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end > start:
            content = content[start:end]
        return json.loads(content)
    except Exception:
        return None

# Geocoding functions (unchanged logic, but will be called only after validation)

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

# Main interactive loop

def main():
    print("Address search & reverse geocoding agent with local LLM (Ollama).")
    print("Type an address or coordinates (e.g., 48.8566, 2.3522). 'quit' to exit.\n")

    while True:
        user_input = input("Input: ").strip()
        if user_input.lower() in ("quit", "q"):
            print("Goodbye.")
            break
        if not user_input:
            continue

        # Coordinates branch (bypass LLM)
        if is_coordinates(user_input):
            lat, lon = parse_coordinates(user_input)
            if lat is None:
                print("Invalid coordinate format.")
                continue
            print(f"Reverse geocoding for {lat}, {lon}...")
            result = reverse_geocode(lat, lon)
            if result:
                print(f"Address: {result.get('display_name')}")
            else:
                print("No address found.")
            continue

        # LLM analysis (address mode)
        llm_result = analyze_with_llm(user_input)

        if llm_result is not None:
            # LLM available
            if llm_result.get("precise", False):
                print(f"Language: {llm_result.get('language', 'unknown')}")
                result = geocode(user_input)
                if result:
                    print(f"Display name: {result.get('display_name')}")
                    print(f"Latitude: {result['lat']}, Longitude: {result['lon']}")
                else:
                    print("Address not found in Nominatim.")
            else:
                print(llm_result.get("message", "Insufficient address details."))
        else:
            # Ollama unavailable – fallback to heuristic checks
            if is_street_only(user_input):
                print("Insufficient: street name without city or postal code.")
                print("Please add a city or postal code (e.g., '12 rue de Rivoli, Paris').")
                continue
            if not has_locality_hint(user_input):
                print("Insufficient: please include a city or postal code.")
                print("Example: '56 rue des fleurs, Calais' or '56 rue des fleurs 62100'.")
                continue
            # Heuristics passed, geocode
            result = geocode(user_input)
            if result:
                print(f"Display name: {result.get('display_name')}")
                print(f"Latitude: {result['lat']}, Longitude: {result['lon']}")
            else:
                print("No result found.")

if __name__ == "__main__":
    main()
