import requests
import re
import json

ollama_model = "llama3.2:1b"
llm_system_prompt = (
    "You are an address parser. Extract the following from the user input, "
    "returning ONLY a strict JSON object with these fields: "
    "{\"language\":\"xx\",\"street\":null,\"city\":null,\"postal_code\":null}. "
    "language: the user language strictly from the user input and return ISO 639-1 code. "
    "street: any recognized thoroughfare (rue, avenue, street, road, etc.) including an optional number, OR null if not found. "
    "city: any recognized populated place name, OR null if not found. "
    "postal_code: any recognized postal/ZIP code, OR null if not found. "
    "No extra text, no markdown. "
    "Try case insensitivity for the street name. "
    "Don't include any other text in the response. "
    "Don't add any other text in the response."
)

# ------------------------------------------------------------
# Fallback heuristic rules (used when Ollama is unavailable)
# ------------------------------------------------------------
STREET_PATTERN = re.compile(
    r"^\s*(rue|avenue|boulevard|place|allée|chemin|impasse|route|square|cours)\b",
    re.IGNORECASE
)

def is_street_only(query):
    """Checks if query contains only a street name. Returns True if present."""
    
    query = query.strip()
    if "," in query:
        return False
    if re.search(r"\d", query):
        return False
    return bool(STREET_PATTERN.match(query))

def has_locality_hint(query):
    """Checks if query contains a locality hint. Returns True if present."""
    
    query = query.strip()
    if "," in query:
        return True
    if re.search(r"(?<!\d)\d{5}(?!\d)", query):
        return True
    return False

# ------------------------------------------------------------
# Ollama availability check
# ------------------------------------------------------------
def is_ollama_available():
    """Checks if Ollama is available. Returns True if reachable."""
    
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False

# ------------------------------------------------------------
# LLM analysis via Ollama
# ------------------------------------------------------------
def analyze_with_llm(text):
    """Returns a dict with keys: language, precise, message (if not precise).
    Returns None if Ollama is not reachable."""
    
    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": ollama_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            llm_system_prompt
                        )
                    },
                    {"role": "user", "content": text}
                ],
                "stream": False,
                "options": {"temperature": 0}
            },
            timeout=20
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

# ------------------------------------------------------------
# Geocoding API calls
# ------------------------------------------------------------
def geocode(address):
    """Geocodes address. Returns address data or None."""
    
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
    """Reverse-geocodes coordinates. Returns address data or None."""
    
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
    """Checks if text looks like coordinates. Returns True if valid."""
    
    pattern = re.compile(r"^\s*([-+]?\d+\.?\d*)\s*[,;\s]\s*([-+]?\d+\.?\d*)\s*$")
    return pattern.match(text) is not None

def parse_coordinates(text):
    """Parses coordinates from text. Returns (lat, lon) tuple or None."""

    pattern = re.compile(r"^\s*([-+]?\d+\.?\d*)\s*[,;\s]\s*([-+]?\d+\.?\d*)\s*$")
    match = pattern.match(text)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None, None

# ------------------------------------------------------------
# Main interactive loop
# ------------------------------------------------------------
def _print_startup_banner(ollama_available):
    """Prints the startup banner."""

    print("Address search & reverse geocoding agent with local LLM (Ollama).\n")
    if ollama_available:
        print("Ollama is running. Enhanced address analysis enabled.\n")
    else:
        print("Ollama not available. Using fallback heuristics.\n")


def _process_coordinate_input(user_input):
    """Reverse-geocode if input looks like coordinates. Returns True if handled."""

    if not is_coordinates(user_input):
        return False
    lat, lon = parse_coordinates(user_input)
    if lat is None:
        print("Invalid coordinate format.")
        return True
    print(f"Reverse geocoding for {lat}, {lon}...")
    result = reverse_geocode(lat, lon)
    if result:
        print(f"Address: {result.get('display_name')}")
    else:
        print("No address found.")
    return True


def _missing_llm_address_labels(has_street, has_city, has_postal):
    """Human-readable missing parts when LLM output is not geocodable."""

    if not has_street and not has_city and not has_postal:
        return ["complete address"]
    has_locality = has_city or has_postal
    missing = []
    if not has_street:
        missing.append("street")
    if not has_locality:
        missing.append("city or postal code")
    return missing


def _print_nominatim_geocode_for_input(user_input):
    """Geocode user_input via Nominatim and print result or not-found."""

    result = geocode(user_input)
    if result:
        print(f"Display name: {result.get('display_name')}")
        print(f"Latitude: {result['lat']}, Longitude: {result['lon']}")
    else:
        print("Address not found in Nominatim.")


def _process_llm_address_input(user_input):
    """LLM path when Ollama works. Returns True if loop should continue."""

    llm_result = analyze_with_llm(user_input)
    if not llm_result:
        print("(LLM call failed, falling back to heuristics)")
        return False

    has_street = llm_result.get("street") not in [None, "", "null"]
    has_city = llm_result.get("city") not in [None, "", "null"]
    has_postal = llm_result.get("postal_code") not in [None, "", "null"]
    has_locality = has_city or has_postal

    if not (has_street and has_locality):
        missing = _missing_llm_address_labels(has_street, has_city, has_postal)
        print(f"Insufficient address. Missing: {', '.join(missing)}.")
        return True

    print(f"Language: {llm_result.get('language', 'unknown')}")
    _print_nominatim_geocode_for_input(user_input)
    return True


def _process_heuristic_geocode(user_input):
    """Fallback path when LLM is not available. Returns True if loop should continue."""

    if is_street_only(user_input):
        print("Insufficient: street name without city or postal code.")
        print("Please add a city or postal code (e.g., '12 rue de Rivoli, Paris').")
        return True
    if not has_locality_hint(user_input):
        print("Insufficient: please include a city or postal code.")
        print("Example: '56 rue des fleurs, Calais' or '56 rue des fleurs 62100'.")
        return True
    result = geocode(user_input)
    if result:
        print(f"Display name: {result.get('display_name')}")
        print(f"Latitude: {result['lat']}, Longitude: {result['lon']}")
    else:
        print("No result found.")
    return False


def main():
    """Main loop: handles user input, LLM calls, and fallback logic."""

    ollama_available = is_ollama_available()
    _print_startup_banner(ollama_available)

    while True:
        user_input = input("Input: ").strip()
        lowered = user_input.lower()
        if lowered in ("quit", "q"):
            print("Goodbye.")
            break
        if not user_input:
            continue
        if _process_coordinate_input(user_input):
            continue
        if ollama_available and _process_llm_address_input(user_input):
            continue
        if _process_heuristic_geocode(user_input):
            continue

if __name__ == "__main__":
    main()
