import math
import os
from django.http import JsonResponse
from rest_framework.decorators import api_view
from amadeus import Client, ResponseError
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")

amadeus = Client(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
)

# todo: break this into multiple functions so they can be re-used for other API endpoints
# e.g. find just a plane to a destination, or just points of interest etc

@api_view(['GET'])
def get_flight_offers(request):
    try:
        data = request.data 
        
        origin = data.get("originLocationCode", "BUH")
        destination = data.get("destinationLocationCode", "JFK")
        departure_date = data.get("departureDate", "2025-03-15")
        adults = data.get("adults", 1)
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

        # search for hotels
        hotel_response = amadeus.reference_data.locations.hotels.by_city.get(cityCode=destination)
        hotel_ids = []
        cnt = 0
        if hotel_response.data:
            for hotel in hotel_response.data:
                if cnt == 5: # temporary(?) 5 hotel limit, as the API does not have a count/max parameter
                    break
                cnt += 1
                hotel_ids.append(hotel["hotelId"])
        rooms = str(math.ceil(adults / 2))
        hotel_offers_response = amadeus.shopping.hotel_offers_search.get(hotelIds=hotel_ids, adults="2", roomQuantity=rooms, checkInDate=departure_date)
        hotel_offers = []
        if hotel_offers_response.data:
            for hotel in hotel_offers_response.data[0]["offers"]:
                # todo: filter the information received and only return useful stuff
                hotel_offers.append(hotel)
        
        # no need to error in case no hotels are found, just gonna inform the user that we couldn't find any
        # and link them to a booking.com link with their city of destination
        # todo: perhaps search for points of interest
        return JsonResponse({"flights": flight_offers, "hotels": hotel_offers}, safe=False, json_dumps_params={'indent': 2})
    
    except ResponseError as error:
        return JsonResponse({"error": str(error)}, status=400)
