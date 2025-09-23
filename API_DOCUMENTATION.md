# MeteoLux API Integration

This document describes how the MeteoLux Home Assistant integration uses the MeteoLux API to provide weather forecasts.

## API Endpoints Used

The integration attempts to use the following endpoints in order:

1. **Primary API**: `https://metapi.ana.lu/api/v1/weather`
2. **Alternative API**: `https://metapi.ana.lu/api/v1/metapp/weather` 
3. **Fallback CSV**: `https://data.public.lu/en/datasets/r/c05ecc27-aa44-4c96-bece-6149783e1758`

## Data Structure

### New API Response Format

The integration expects the following JSON structure from the MeteoLux API:

```json
{
  "current": {
    "datetime": "ISO format datetime",
    "temperature": 18.5,
    "humidity": 65,
    "pressure": 1015.2,
    "wind": {
      "speed": 12.3,
      "direction": "SW"
    },
    "visibility": 10000,
    "weather": {
      "description": "Weather condition description"
    }
  },
  "daily": [
    {
      "datetime": "ISO format datetime",
      "temperature": {
        "max": 22.1,
        "min": 12.8
      },
      "precipitation": 0.2,
      "wind": {
        "speed": 15.5,
        "direction": "W"
      },
      "humidity": 68,
      "pressure": 1014.8,
      "weather": {
        "description": "Weather condition description"
      }
    }
  ],
  "hourly": [
    {
      "datetime": "ISO format datetime",
      "temperature": 19.2,
      "precipitation": 0.1,
      "wind": {
        "speed": 11.8,
        "direction": "SW"
      },
      "humidity": 63,
      "pressure": 1015.5,
      "cloud_coverage": 45,
      "weather": {
        "description": "Weather condition description"
      }
    }
  ]
}
```

## Weather Condition Mapping

The integration maps MeteoLux weather descriptions to Home Assistant weather conditions using an extensive condition map that supports both English and French descriptions.

## Features Provided

### Weather Entity

- **Current conditions**: Temperature, humidity, pressure, wind speed/direction, visibility
- **Hourly forecasts**: Up to 48 hours of detailed forecasts
- **Daily forecasts**: Up to 7 days of daily forecasts

### Sensors

- Temperature sensors (min/max for day, and period-specific)
- Precipitation sensors for different time periods
- Wind speed and direction sensors
- Weather condition description sensors

## Fallback Behavior

If the primary API endpoints fail, the integration automatically falls back to the legacy CSV data source to ensure continued operation. The CSV format provides limited daily forecast data with morning, afternoon, and evening periods.

## Error Handling

The integration includes comprehensive error handling:

- Connection timeouts and network errors
- HTTP status code errors (404, 500, etc.)
- Invalid or malformed JSON responses
- Missing data fields in responses

## API Compliance

This integration complies with:
- High Value Dataset (HVD) Implementing Regulation (EU) 2023/138
- Creative Commons Public Domain Dedication (CC0) license terms
- MeteoLux terms of service for API usage

## Configuration

No configuration is required. The integration automatically:
1. Tries the new API endpoints first
2. Falls back to CSV data if needed
3. Updates data every 30 minutes
4. Handles missing or incomplete data gracefully
