from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from django.http import JsonResponse
from amadeus import ResponseError

from .services.hotel_services import create_booking_url
from .services.travel_services import generate_travel_tips, get_landmarks, get_weather_forecast
from .services.flight_services import get_airport_info, get_flight_offers, process_flight_offers
from datetime import datetime


@api_view(['GET'])
@permission_classes([IsAuthenticated])
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
                "landmarks": get_landmarks(dest_airport['city'], dest_airport["country"]),
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
