import streamlit as st
import pandas as pd
from agent import (
    geocode, reverse_geocode,
    is_coordinates, parse_coordinates,
    analyze_with_llm, is_ollama_available,
    is_street_only, has_locality_hint,
)

# Page configuration
st.set_page_config(page_title="Address Agent", page_icon="📍", layout="centered")
st.title("Address & GPS Coordinates Search Agent")

# Check Ollama availability (once per session)
if "ollama_available" not in st.session_state:
    st.session_state.ollama_available = is_ollama_available()

ollama_ok = st.session_state.ollama_available
if ollama_ok:
    st.success("✅ Ollama detected – intelligent analysis enabled")
else:
    st.warning("⚠️ Ollama not available – using basic heuristics")

# User input
with st.form("address_form"):
    user_input = st.text_input(
        "Enter an address or coordinates (e.g., 48.8566, 2.3522):",
        placeholder="12 rue de Rivoli, Paris"
    )
    submitted = st.form_submit_button("Search")

if submitted and user_input.strip():
    query = user_input.strip()
    st.divider()

    # -------- GPS Coordinates ----------
    if is_coordinates(query):
        lat, lon = parse_coordinates(query)
        if lat is None:
            st.error("Invalid coordinate format. Use `lat, lon`.")
        else:
            with st.spinner("Reverse geocoding..."):
                result = reverse_geocode(lat, lon)
            if result:
                # Map
                map_df = pd.DataFrame({"lat": [lat], "lon": [lon]})
                st.map(map_df, zoom=15)
                st.success(f"**Address found**: {result.get('display_name')}")
            else:
                st.error("No address found for these coordinates.")
        st.stop()   # Coordinates processed, stop here

    # -------- Textual address ----------
    if ollama_ok:
        # LLM path
        with st.spinner("Analyzing with LLM (Ollama)..."):
            llm_result = analyze_with_llm(query)
        if llm_result is None:
            st.warning("LLM call failed, falling back to heuristics.")
            # fallback to heuristics below
        else:
            has_street = llm_result.get("street") not in [None, "", "null"]
            has_city = llm_result.get("city") not in [None, "", "null"]
            has_postal = llm_result.get("postal_code") not in [None, "", "null"]
            has_locality = has_city or has_postal

            if has_street and has_locality:
                st.caption(f"🌍 Detected language: {llm_result.get('language', 'unknown')}")
                with st.spinner("Geocoding via Nominatim..."):
                    geocode_result = geocode(query)
                if geocode_result:
                    lat, lon = float(geocode_result["lat"]), float(geocode_result["lon"])
                    map_df = pd.DataFrame({"lat": [lat], "lon": [lon]})
                    st.map(map_df, zoom=15)
                    st.success(f"**Address found**: {geocode_result.get('display_name')}")
                    st.text(f"Latitude: {lat}  |  Longitude: {lon}")
                else:
                    st.error("Address not found in Nominatim.")
            else:
                # Incomplete address -> custom message
                missing = []
                if not has_street and not has_city and not has_postal:
                    missing.append("a complete address (street + city or postal code)")
                else:
                    if not has_street:
                        missing.append("street")
                    if not has_locality:
                        missing.append("city or postal code")
                missing_str = ", ".join(missing)
                st.warning(f"Insufficient address. Please provide {missing_str}.")
            st.stop()   # LLM processing done

    # -------- Fallback heuristics (Ollama unavailable or failed) ----------
    if is_street_only(query):
        st.warning("The input appears to be a street name without a city or postal code.")
        st.info("Please add a city or postal code (e.g., '12 rue de Rivoli, Paris').")
    elif not has_locality_hint(query):
        st.warning("Please include a city or postal code along with the street.")
        st.info("Example: '56 rue des fleurs, Calais' or '56 rue des fleurs 62100'.")
    else:
        with st.spinner("Geocoding via Nominatim..."):
            geocode_result = geocode(query)
        if geocode_result:
            lat, lon = float(geocode_result["lat"]), float(geocode_result["lon"])
            map_df = pd.DataFrame({"lat": [lat], "lon": [lon]})
            st.map(map_df, zoom=15)
            st.success(f"**Address found**: {geocode_result.get('display_name')}")
            st.text(f"Latitude: {lat}  |  Longitude: {lon}")
        else:
            st.error("Address not found in Nominatim.")
