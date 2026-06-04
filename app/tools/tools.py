import os
import requests
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


def _normalize_destination(destination):
    if not destination:
        return destination

    normalized = destination.strip()
    aliases = {
        "udaypur": "Udaipur",
        "udayapur": "Udaipur",
        "banglore": "Bangalore",
        "banaras": "Varanasi"
    }

    return aliases.get(normalized.lower(), normalized)


def weather_tool(destination):
    destination = _normalize_destination(destination)
    api_key = os.getenv("OPENWEATHER_API_KEY")

    # Primary source: OpenWeather (requires API key)
    if api_key:
        try:
            url = (
                "https://api.openweathermap.org/data/2.5/weather"
                f"?q={quote_plus(destination)}"
                f"&appid={api_key}"
                "&units=metric"
            )
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            weather = data["weather"][0]["main"]
            temp = data["main"]["temp"]
            return f"{weather}, {temp}°C"
        except Exception:
            pass

    # Fallback source: wttr.in (no API key)
    try:
        fallback_url = f"https://wttr.in/{quote_plus(destination)}?format=j1"
        fallback_response = requests.get(fallback_url, timeout=10)
        fallback_response.raise_for_status()
        fallback_data = fallback_response.json()
        current = fallback_data["current_condition"][0]
        weather = current["weatherDesc"][0]["value"]
        temp = current["temp_C"]
        return f"{weather}, {temp}°C"
    except Exception:
        return "Weather temporarily unavailable"


def hotel_cost_tool(destination):
    hotel_data = {
        "Goa": 2500,
        "Jaipur": 1800,
        "Manali": 2200
    }
    return hotel_data.get(destination, 2000)


def food_cost_tool(destination):
    food_data = {
        "Goa": 1000,
        "Jaipur": 800,
        "Manali": 900
    }
    return food_data.get(destination, 1000)
