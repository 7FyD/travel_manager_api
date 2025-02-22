import math
import os
from django.http import JsonResponse
from rest_framework.decorators import api_view
from amadeus import Client, ResponseError
from dotenv import load_dotenv
import airportsdata

load_dotenv()
CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")

amadeus = Client(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
)

# todo: break this into multiple functions so they can be re-used for other API endpoints
# e.g. find just a plane to a destination, or just points of interest etc

# this uses airportsdata to fetch the city and country from an airport IATA code
def get_airport_info(airport_code):
    airports = airportsdata.load('IATA')
    if airport_code in airports:
        airport = airports[airport_code]
        city = airport['city']
        country = airport['country']
        return city, country
    else:
        return "Airport not found.", "N/A"

# this dynamically creates booking links for the customer's destionation with proper dates and other data
def create_booking_url(airport_code, checkin_date, checkout_date, adults, children):
    city, country = get_airport_info(airport_code)
    if country == "N/A":
        return city  # todo: return error

    checkin_year, checkin_month, checkin_day = checkin_date.split('-')
    checkout_year, checkout_month, checkout_day = checkout_date.split('-')

    # generate a booking link for the destionation
    url = (
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

    return url

@api_view(['GET'])
def get_flight_offers(request):
    try:
        data = request.data 
        
        origin = data.get("originLocationCode", "BUH")
        destination = data.get("destinationLocationCode", "MBJ")
        departure_date = data.get("departureDate", "2025-03-15")
        adults = data.get("adults", 1)
        children = data.get("children", 0)
        currency = data.get("currencyCode", "EUR")
        max_results = data.get("max", 5)
        travel_class = data.get("travelClass", "BUSINESS")

        # required_fields = ["originLocationCode", "destinationLocationCode", "departureDate"]
        # for field in required_fields:
        #     if field not in data or not data[field]:
        #         return JsonResponse({"error": f"Missing required field: {field}"}, status=400)
        
        # origin = data["originLocationCode"]
        # destination = data["destinationLocationCode"]
        # departure_date = data["departureDate"]
        # adults = data.get("adults", 1)
        # currency = data.get("currencyCode", "EUR")
        # max_results = data.get("max", 5)
        # travel_class = data.get("travelClass", "BUSINESS")
        
        # fetch all flight offers with specified data
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=departure_date,
            adults=adults,
            currencyCode=currency,
            max=max_results,
            travelClass=travel_class,
        )
        if not response.data:
            return JsonResponse({"error": "No flights found for the given criteria."}, status=404)
        
        flight_offers = []
        # store the important data about each flight and its segments 
        for offer in response.data:
            offer_info = {
                "id": offer["id"],
                "price": offer["price"]["total"],
                "currency": offer["price"]["currency"],
                "airlines": ", ".join(offer.get("validatingAirlineCodes", [])),
                "itineraries": []
            }
            
            for itinerary in offer["itineraries"]:
                itinerary_info = {
                    "duration": itinerary["duration"],
                    "segments": []
                }
                
                for segment in itinerary["segments"]:
                    segment_info = {
                        "departure": {
                            "iataCode": segment["departure"]["iataCode"],
                            "at": segment["departure"]["at"]
                        },
                        "arrival": {
                            "iataCode": segment["arrival"]["iataCode"],
                            "at": segment["arrival"]["at"]
                        },
                        "carrierCode": segment["carrierCode"],
                        "flightNumber": segment["number"],
                        "duration": segment["duration"]
                    }
                    itinerary_info["segments"].append(segment_info)
                
                offer_info["itineraries"].append(itinerary_info)
            
            flight_offers.append(offer_info)
        
        if len(flight_offers) < 1:
            return JsonResponse({"error": "No flights found for the given criteria."}, status=404)

        rooms = str(math.ceil(adults / 2))
        # todo:     
        hotels_link = create_booking_url(destination, departure_date, "2025-05-19", adults, children)
        # todo: perhaps search for points of interest
        return JsonResponse({"flights": flight_offers, "hotels": hotels_link}, safe=False, json_dumps_params={'indent': 2})
    
    except ResponseError as error:
        return JsonResponse({"error": str(error)}, status=400)
