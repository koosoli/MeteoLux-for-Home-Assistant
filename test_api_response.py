"""Test script to check MeteoLux API response structure."""
import asyncio
import aiohttp
import json


async def test_meteolux_api():
    """Test the MeteoLux API endpoints to see actual response structure."""
    
    endpoints = [
        "https://metapi.ana.lu/api/v1/weather",
        "https://metapi.ana.lu/api/v1/metapp/weather",
    ]
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            print(f"\n=== Testing endpoint: {endpoint} ===")
            try:
                async with session.get(endpoint) as response:
                    print(f"Status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        print("Response structure:")
                        print(json.dumps(data, indent=2, default=str)[:2000])  # Limit output
                    else:
                        print(f"Error: {response.status}")
                        text = await response.text()
                        print(f"Response: {text[:500]}")
            except Exception as e:
                print(f"Exception: {e}")


if __name__ == "__main__":
    asyncio.run(test_meteolux_api())
