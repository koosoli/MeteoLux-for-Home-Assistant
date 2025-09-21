"""Constants for the MeteoLux integration."""
from datetime import time

DOMAIN = "meteolux"

DATA_URL = "https://data.public.lu/en/datasets/r/c05ecc27-aa44-4c96-bece-6149783e1758"

CONDITION_MAP = {
    "Clear sky": "sunny",
    "Partly cloudy": "partlycloudy",
    "Cloudy": "cloudy",
    "Overcast": "cloudy",
    "Light rain": "rainy",
    "Moderate rain": "rainy",
    "Heavy rain": "pouring",
    "Drizzle": "rainy",
    "Fog": "fog",
    "Snow": "snowy",
    "Sleet": "sleet",
    # Add French conditions if needed, assuming API can be multilingual
    "Ciel dégagé": "sunny",
    "Partiellement nuageux": "partlycloudy",
    "Nuageux": "cloudy",
    "Couvert": "cloudy",
    "Pluie faible": "rainy",
    "Pluie modérée": "rainy",
    "Pluie forte": "pouring",
    "Bruine": "rainy",
    "Brouillard": "fog",
    "Neige": "snowy",
    "Neige fondue": "sleet",
}

FORECAST_TIMES = {
    "morning": time(8, 0, 0),
    "afternoon": time(14, 0, 0),
    "evening": time(20, 0, 0),
}
