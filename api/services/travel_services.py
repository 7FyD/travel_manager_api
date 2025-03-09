from datetime import datetime, timedelta
import os
from google import genai
import requests

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ai_client = genai.Client(api_key=GEMINI_API_KEY)


def get_landmarks(city, country):
    try:
        response = ai_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"""What are some points of interest to visit in {city}s, {country}?\n
              Respond in a JSON-like object only with the following data about 3-5 points of interest:
              name, category, address and a short ~-2 sentece description. \n
              Respond in a JSON format, without specifying that its a JSON. Do not add any other characters besides the JSON object.
              Use the following format:\n\n
              "points_of_interest": [
                "name": name_of_landmark,\n
                "category": category,\n
                "address": physical address,\n
                "description": short ~2 sentence description\n\n
              ]
              """)
        return response.text
    except Exception as e:
        print(f"Landmarks error: {e}")
        return []


def get_weather_icon(code):
    """Map Open-Meteo weather codes to OpenWeatherMap icons"""
    icon_map = {
        0: "01d",   # Clear sky
        1: "02d",   # Mainly clear
        2: "03d",   # Partly cloudy
        3: "04d",   # Overcast
        45: "50d",  # Fog
        48: "50d",  # Depositing rime fog
        51: "09d",  # Light drizzle
        53: "09d",  # Moderate drizzle
        55: "09d",  # Dense drizzle
        56: "13d",  # Light freezing drizzle
        57: "13d",  # Dense freezing drizzle
        61: "10d",  # Slight rain
        63: "10d",  # Moderate rain
        65: "10d",  # Heavy rain
        66: "13d",  # Light freezing rain
        67: "13d",  # Heavy freezing rain
        71: "13d",  # Slight snow fall
        73: "13d",  # Moderate snow fall
        75: "13d",  # Heavy snow fall
        77: "13d",  # Snow grains
        80: "09d",  # Slight rain showers
        81: "09d",  # Moderate rain showers
        82: "09d",  # Violent rain showers
        85: "13d",  # Slight snow showers
        86: "13d",  # Heavy snow showers
        95: "11d",  # Thunderstorm
        96: "11d",  # Thunderstorm with hail
        99: "11d"   # Thunderstorm with heavy hail
    }
    return icon_map.get(code, "02d")


def get_weather_forecast(lat, lon, checkin_date, checkout_date):
    try:
        today = datetime.now().date()
        check_in = datetime.strptime(checkin_date, "%Y-%m-%d").date()
        check_out = datetime.strptime(checkout_date, "%Y-%m-%d").date()

        days_until_checkin = (check_in - today).days

        # if the trip is less than 15 days in the future, provide current weather information, otherwise return same dates last year
        if days_until_checkin <= 14 and days_until_checkin >= 0:

            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                "forecast_days": 14,
                "timezone": "auto"
            }
            old_dates = False
        else:
            trip_duration = (check_out - check_in).days + 1
            total_days_needed = 14

            if trip_duration >= total_days_needed:

                mid_point = check_in + timedelta(days=trip_duration // 2)
                start_date = mid_point - timedelta(days=total_days_needed//2)
                end_date = start_date + timedelta(days=total_days_needed-1)
            else:
                days_before = (total_days_needed - trip_duration) // 2
                days_after = total_days_needed - trip_duration - days_before
                start_date = check_in - timedelta(days=days_before)
                end_date = check_out + timedelta(days=days_after)

            historical_year = check_in.year - 1
            start_date = start_date.replace(year=historical_year)
            end_date = end_date.replace(year=historical_year)

            url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                "timezone": "auto"
            }
            old_dates = True

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        daily = data['daily']
        weather_data = []
        for i in range(len(daily['time'])):
            weather_entry = {
                "date": daily['time'][i],
                "temp": daily['temperature_2m_max'][i],
                "temp_min": daily['temperature_2m_min'][i],
                "temp_max": daily['temperature_2m_max'][i],
                "weather_code": daily['weather_code'][i],
                "icon": f"http://openweathermap.org/img/wn/{get_weather_icon(daily['weather_code'][i])}.png"
            }
            weather_data.append(weather_entry)

        return {"old_dates": old_dates, "daily_data": weather_data[:14]}

    except Exception as e:
        print(f"Weather API error: {str(e)}")
        return []


def generate_travel_tips(city, country, days):
    try:
        response = ai_client.models.generate_content(
            model="gemini-2.0-flash", contents=f"""Give 5 concise tips for visiting {city}, {country} for {days} days.
              Respond in a JSON format, without specifying that its a JSON. Do not add any other characters besides the JSON object.\n              
              Use the following format:\n\n
              [
              "day": day of the trip,\n
              "tip": the tip,\n
              ]
              """)
        return response.text
    except Exception as e:
        print(f"Generative AI error: {e}")
        return None
