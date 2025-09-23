# MeteoLux Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)

This is a custom integration for Home Assistant that provides weather information from [MeteoLux](https://www.meteolux.lu/), the national meteorological service of Luxembourg.

The integration fetches data from the official MeteoLux API and provides both current weather conditions and detailed forecasts including hourly and daily forecasts.

## Features

- **Current Weather**: Real-time weather conditions including temperature, humidity, pressure, wind speed/direction, and visibility
- **Hourly Forecast**: Up to 48 hours of detailed weather forecasts
- **Daily Forecast**: Up to 7 days of daily weather forecasts  
- **Comprehensive Weather Data**: Precipitation, cloud coverage, and detailed weather descriptions
- **Automatic Fallback**: Falls back to CSV data source if the main API is unavailable

## Installation

### HACS (Home Assistant Community Store)

1.  Go to HACS -> Integrations.
2.  Click on the 3 dots in the top right corner and select "Custom repositories".
3.  Add the URL of this repository (`https://github.com/koosoli/MeteoLux-for-Home-Assistant`) and select "Integration" as the category.
4.  Click "Add".
5.  The "MeteoLux" integration will now be available to install. Click "Install".
6.  Restart Home Assistant.

## Configuration

1.  Go to **Settings** -> **Devices & Services**.
2.  Click the **+ Add Integration** button.
3.  Search for "MeteoLux" and click on it.
4.  The integration will be added and a weather entity and several sensors will be created. No further configuration is needed.

## Provided Entities

### Weather

-   `weather.meteolux`: A weather entity that provides current conditions and forecasts for Luxembourg.
    - Supports both hourly and daily forecasts
    - Provides current temperature, humidity, pressure, wind data, and visibility
    - Automatically maps weather conditions to Home Assistant icons

### Sensors

The integration provides the following sensors:

-   `sensor.meteolux_max_temperature`: The maximum temperature for the day.
-   `sensor.meteolux_min_temperature`: The minimum temperature for the day.
-   `sensor.meteolux_morning_precipitation`: The forecasted precipitation for the morning.
-   `sensor.meteolux_afternoon_precipitation`: The forecasted precipitation for the afternoon.
-   `sensor.meteolux_evening_precipitation`: The forecasted precipitation for the evening.
-   And many more sensors for different time periods covering temperature, precipitation, wind conditions, and weather descriptions.

## Data Sources

This integration uses multiple data sources for maximum reliability:

1. **Primary**: [MeteoLux API](https://metapi.ana.lu/api/v1/) - Provides comprehensive current weather and forecast data
2. **Fallback**: Open data CSV from [data.public.lu](https://data.public.lu/en/datasets/meteolux-luxembourg-weather-forecast-for-the-current-day/) - Provides daily forecast periods

The integration automatically tries the primary API first and falls back to the CSV data source if needed, ensuring continuous operation.

## API Compliance

This integration complies with the High Value Dataset (HVD) Implementing Regulation (EU) 2023/138 and uses free access to real-time meteorological data from Luxembourg.
