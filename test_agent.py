# test_agent.py
import pytest
import requests_mock
from agent import (
    is_street_only,
    has_locality_hint,
    is_ollama_available,
    analyze_with_llm,
    geocode,
    reverse_geocode,
    is_coordinates,
    parse_coordinates,
)

# ------------------------------------------------------------------------------
# Tests for is_street_only
# ------------------------------------------------------------------------------
def test_is_street_only_simple():
    assert is_street_only("Rue de la Paix") is True

def test_is_street_only_with_number():
    assert is_street_only("12 Rue de la Paix") is False

def test_is_street_only_with_comma():
    assert is_street_only("Rue de la Paix, Paris") is False

def test_is_street_only_city_only():
    assert is_street_only("Paris") is False

def test_is_street_only_empty():
    assert is_street_only("") is False

def test_is_street_only_leading_spaces():
    assert is_street_only("  avenue des Champs") is True

# ------------------------------------------------------------------------------
# Tests for has_locality_hint
# ------------------------------------------------------------------------------
def test_has_locality_hint_comma():
    assert has_locality_hint("Rue de Rivoli, Paris") is True

def test_has_locality_hint_zipcode():
    assert has_locality_hint("Rue de Rivoli 75001") is True

def test_has_locality_hint_zipcode_alone():
    assert has_locality_hint("75001") is True

def test_has_locality_hint_no_hint():
    assert has_locality_hint("Rue de Rivoli") is False

def test_has_locality_hint_empty():
    assert has_locality_hint("") is False

# ------------------------------------------------------------------------------
# Tests for is_ollama_available
# ------------------------------------------------------------------------------
def test_is_ollama_available_true():
    with requests_mock.Mocker() as m:
        m.get("http://localhost:11434/api/tags", status_code=200)
        assert is_ollama_available() is True

def test_is_ollama_available_false():
    with requests_mock.Mocker() as m:
        m.get("http://localhost:11434/api/tags", status_code=500)
        assert is_ollama_available() is False

def test_is_ollama_available_connection_error():
    with requests_mock.Mocker() as m:
        m.get("http://localhost:11434/api/tags", exc=ConnectionError)
        assert is_ollama_available() is False

# ------------------------------------------------------------------------------
# Tests for analyze_with_llm
# ------------------------------------------------------------------------------
def test_analyze_precise():
    with requests_mock.Mocker() as m:
        m.post(
            "http://localhost:11434/api/chat",
            json={
                "message": {
                    "content": '{"language":"fr","precise":true,"message":""}'
                }
            },
        )
        result = analyze_with_llm("12 rue de Rivoli, Paris")
        assert result == {"language": "fr", "precise": True, "message": ""}

def test_analyze_not_precise():
    with requests_mock.Mocker() as m:
        m.post(
            "http://localhost:11434/api/chat",
            json={
                "message": {
                    "content": '{"language":"en","precise":false,"message":"Please provide a city."}'
                }
            },
        )
        result = analyze_with_llm("Rue de Rivoli")
        assert result["precise"] is False
        assert "city" in result["message"]

def test_analyze_llm_error_returns_none():
    with requests_mock.Mocker() as m:
        m.post("http://localhost:11434/api/chat", exc=ConnectionError)
        result = analyze_with_llm("anything")
        assert result is None

# ------------------------------------------------------------------------------
# Tests for geocode
# ------------------------------------------------------------------------------
def test_geocode_success():
    with requests_mock.Mocker() as m:
        url = "https://nominatim.openstreetmap.org/search"
        m.get(
            url,
            json=[
                {
                    "display_name": "Test Address",
                    "lat": "48.8566",
                    "lon": "2.3522",
                    "addresstype": "house",
                    "address": {"city": "Paris"},
                }
            ],
        )
        result = geocode("Test query")
        assert result is not None
        assert result["lat"] == "48.8566"

def test_geocode_empty():
    with requests_mock.Mocker() as m:
        url = "https://nominatim.openstreetmap.org/search"
        m.get(url, json=[])
        result = geocode("Test query")
        assert result is None

def test_geocode_api_error():
    with requests_mock.Mocker() as m:
        url = "https://nominatim.openstreetmap.org/search"
        m.get(url, status_code=500)
        result = geocode("Test query")
        assert result is None

# ------------------------------------------------------------------------------
# Tests for reverse_geocode
# ------------------------------------------------------------------------------
def test_reverse_geocode_success():
    with requests_mock.Mocker() as m:
        url = "https://nominatim.openstreetmap.org/reverse"
        m.get(
            url,
            json={
                "display_name": "Reversed Address",
                "lat": "48.8566",
                "lon": "2.3522",
            },
        )
        result = reverse_geocode(48.8566, 2.3522)
        assert result is not None
        assert result["display_name"] == "Reversed Address"

def test_reverse_geocode_empty():
    with requests_mock.Mocker() as m:
        url = "https://nominatim.openstreetmap.org/reverse"
        m.get(url, json={})
        result = reverse_geocode(0, 0)
        assert result is None

def test_reverse_geocode_api_error():
    with requests_mock.Mocker() as m:
        url = "https://nominatim.openstreetmap.org/reverse"
        m.get(url, status_code=500)
        result = reverse_geocode(48.0, 2.0)
        assert result is None

# ------------------------------------------------------------------------------
# Tests for is_coordinates and parse_coordinates
# ------------------------------------------------------------------------------
def test_is_coordinates_valid():
    assert is_coordinates("48.8566, 2.3522") is True
    assert is_coordinates("-23.5, -46.6") is True
    assert is_coordinates("48.8566,2.3522") is True

def test_is_coordinates_invalid():
    assert is_coordinates("Paris") is False
    assert is_coordinates("48.8566") is False
    assert is_coordinates("") is False

def test_parse_coordinates():
    lat, lon = parse_coordinates("48.8566, 2.3522")
    assert lat == pytest.approx(48.8566)
    assert lon == pytest.approx(2.3522)

def test_parse_coordinates_negative():
    lat, lon = parse_coordinates("-23.5, -46.6")
    assert lat == pytest.approx(-23.5)
    assert lon == pytest.approx(-46.6)

def test_parse_coordinates_invalid():
    lat, lon = parse_coordinates("invalid")
    assert lat is None
    assert lon is None
