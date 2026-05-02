import requests
import re
import json

ollama_model = "gemma3:1b"
llm_system_prompt = (
    "You are an address precision classifier. Your only task is to examine the user's address input "
    "and output a JSON object with exactly the fields: language, precise, message.\n\n"
    "No extra text, no markdown, no explanations.\n\n"
    "You MUST follow these step-by-step rules:\n"
    "  1. Detect the language of the input. Use ISO 639-1 code (e.g., 'fr', 'en'). Place it in the 'language' field.\n"
    "  2. IF the input address contains BOTH a city name AND a postal code WITHOUT a street name : set precise = false.\n"
    "  3. IF the input address contains BOTH a street name AND a city name WITHOUT a postal code : set precise = false.\n"
    "  4. IF the input address contains BOTH a street name AND a postal code WITHOUT a city name : set precise = false.\n"
    "  5. IF the input address contains ONLY a city name : set precise = false.\n"
    "  6. IF the input address contains ONLY a city name WITHOUT a street or a postal code : set precise = false.\n"
    "  7. IF the input address contains ONLY a postal code : set precise = false.\n"
    "  8. IF the input address contains ONLY a postal code WITHOUT a street name OR a city name : set precise = false.\n"
    "  9. IF the input address contains ONLY a street name : set precise = false.\n"
    " 10. IF the input address contains ONLY a street name (with or without a number) WITHOUT a city OR a postal code : set precise = false.\n"
    " 11. IF the input address contains ONLY a street number WITHOUT a city name OR a postal code : set precise = false.\n"
    " 12. IF the input address contains BOTH a street name AND a city name AND a postal code : set precise = true.\n"
    " 13. IF the input address contains ONLY a city name AND a postal code : set precise = true.\n"
    " 14. IF the input address contains ONLY a street name AND a city name : set precise = true.\n"
    " 15. IF the input address contains ONLY a street name AND a city name AND a postal code : set precise = true.\n"
    " 16. IF the input address contains ONLY a street name AND a city name OR a postal code : set precise = true.\n"
    " 17. IF the input address contains ONLY a street name AND a postal code : set precise = true.\n"
    " At the end of the analysis, ONLY if precise is FALSE, set message to a brief, polite sentence in the detected language asking for the missing information."
)

# ------------------------------------------------------------
# Fallback heuristic rules (used when Ollama is unavailable)
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# Ollama availability check
# ------------------------------------------------------------
def is_ollama_available():
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
            timeout=10
        )
        data = response.json()
        content = data["message"]["content"].strip()
        print(content)
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

# ------------------------------------------------------------
# Main interactive loop
# ------------------------------------------------------------
def _print_startup_banner(ollama_available):
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


def _process_llm_address_input(user_input):
    """LLM path when Ollama works. Returns True if loop should continue."""
    llm_result = analyze_with_llm(user_input)
    if llm_result is None:
        print("(LLM call failed, falling back to heuristics)")
        return False
    if llm_result.get("precise", False):
        # The LLM confirmed the address is complete → geocode
        print(f"Language: {llm_result.get('language', 'unknown')}")
        result = geocode(user_input)
        if result:
            print(f"Display name: {result.get('display_name')}")
            print(f"Latitude: {result['lat']}, Longitude: {result['lon']}")
        else:
            print("Address not found in Nominatim.")
    else:
        # Address incomplete → show the LLM's polite message
        print(llm_result.get("message", "Insufficient address details."))
    return True


def _process_heuristic_geocode(user_input):
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
