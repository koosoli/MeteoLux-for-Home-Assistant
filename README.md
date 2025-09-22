# MeteoLux Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)

This is a custom integration for Home Assistant that provides weather information from [MeteoLux](https://www.meteolux.lu/), the national meteorological service of Luxembourg.

The integration fetches data from the official MeteoLux open data feed, which is updated daily.

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

-   `weather.meteolux`: A weather entity that provides the daily forecast for Luxembourg.

### Sensors

The integration provides the following sensors:

-   `sensor.meteolux_max_temperature`: The maximum temperature for the day.
-   `sensor.meteolux_min_temperature`: The minimum temperature for the day.
-   `sensor.meteolux_morning_precipitation`: The forecasted precipitation for the morning.
-   `sensor.meteolux_afternoon_precipitation`: The forecasted precipitation for the afternoon.
-   `sensor.meteolux_evening_precipitation`: The forecasted precipitation for the evening.

## Data Source

This integration uses open data provided by the Luxembourg government on the [data.public.lu](https://data.public.lu/en/datasets/meteolux-luxembourg-weather-forecast-for-the-current-day/) portal.
