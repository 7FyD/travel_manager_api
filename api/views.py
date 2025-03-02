import os
import requests
from django.http import JsonResponse
from rest_framework.decorators import api_view
from amadeus import Client, ResponseError
from dotenv import load_dotenv
from google import genai
import airportsdata
from datetime import datetime, timedelta

load_dotenv()

# api keys
CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")
OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ai_client = genai.Client(api_key=GEMINI_API_KEY)
amadeus = Client(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
airports = airportsdata.load('IATA')


def get_airport_info(airport_code):
    return airports.get(airport_code, None)


def create_booking_url(airport_code, checkin_date, checkout_date, adults, children):
    airport_info = get_airport_info(airport_code)
    if not airport_info:
        return None

    try:
        checkin_year, checkin_month, checkin_day = checkin_date.split('-')
        checkout_year, checkout_month, checkout_day = checkout_date.split('-')
    except ValueError:
        return None

    city = airport_info['city']
    country = airport_info['country']
    return (
        f"https://www.booking.com/searchresults.html?"
        f"ss={city}+{country}&"
        f"checkin_year={checkin_year}&"
        f"checkin_month={checkin_month}&"
        f"checkin_monthday={checkin_day}&"
        f"checkout_year={checkout_year}&"
        f"checkout_month={checkout_month}&"
        f"checkout_monthday={checkout_day}&"
        f"group_adults={adults}&"
        f"group_children={children}"
    )


def get_flight_offers(origin, destination, departure_date, adults, currency, max_results, travel_class):
    try:
        return amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=departure_date,
            adults=adults,
            currencyCode=currency,
            max=max_results,
            travelClass=travel_class,
        ).data
    except ResponseError as e:
        raise e


def process_flight_offers(flight_data):
    return [{
        "id": offer["id"],
        "price": offer["price"]["total"],
        "currency": offer["price"]["currency"],
        "airlines": ", ".join(offer.get("validatingAirlineCodes", [])),
        "itineraries": [{
            "duration": itinerary["duration"],
            "segments": [{
                "departure": segment["departure"],
                "arrival": segment["arrival"],
                "carrierCode": segment["carrierCode"],
                "flightNumber": segment["number"],
                "duration": segment["duration"]
            } for segment in itinerary["segments"]]
        } for itinerary in offer["itineraries"]]
    } for offer in flight_data]


def get_landmarks(city):
    try:
        response = ai_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"""What are some points of interest to visit in {city}?
              Respond in a JSON-like object only with the following data about 3-5 points of interest:
              name, category, address and a short ~-2 sentece description.""")
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
            model="gemini-2.0-flash", contents=f"Give 5 concise tips for visiting {city}, {country} for {days} days. Include cultural norms and safety.")
        return response.text
    except Exception as e:
        print(f"GPT error: {e}")
        return None

# main Endpoint


@api_view(['GET'])
def travel_planner(request):
    try:
        params = request.query_params
        required_fields = ["originLocationCode", "destinationLocationCode",
                           "departureDate", "checkInDate", "checkOutDate"]
        if any(f not in params for f in required_fields):
            return JsonResponse({"error": "Missing required parameters"}, status=400)

        origin = params["originLocationCode"]
        destination = params["destinationLocationCode"]
        checkin_date = params["checkInDate"]
        checkout_date = params["checkOutDate"]
        trip_days = (datetime.strptime(checkout_date, "%Y-%m-%d") -
                     datetime.strptime(checkin_date, "%Y-%m-%d")).days + 1

        dest_airport = get_airport_info(destination)
        if not dest_airport:
            return JsonResponse({"error": "Invalid destination airport"}, status=400)

        flight_data = get_flight_offers(
            origin, destination,
            params["departureDate"],
            int(params.get("adults", 1)),
            params.get("currencyCode", "EUR"),
            int(params.get("max", 5)),
            params.get("travelClass", "BUSINESS")
        )

        response_data = {
            "flights": process_flight_offers(flight_data),
            "hotels": create_booking_url(
                destination,
                checkin_date,
                checkout_date,
                int(params.get("adults", 1)),
                int(params.get("children", 0))
            ),
            "destination_info": {
                "city": dest_airport['city'],
                "country": dest_airport['country'],
                "weather": get_weather_forecast(dest_airport['lat'], dest_airport['lon'], checkin_date=checkin_date, checkout_date=checkout_date),
                "landmarks": get_landmarks(dest_airport['city']),
                "travel_tips": generate_travel_tips(
                    dest_airport['city'],
                    dest_airport['country'],
                    trip_days
                ),
            },
            "trip_duration": f"{trip_days} days"
        }

        return JsonResponse(response_data, safe=False, json_dumps_params={'indent': 2})

    except ResponseError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
