import os
from django.http import JsonResponse
from rest_framework.decorators import api_view
from amadeus import Client, ResponseError
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID=os.getenv("AMADEUS_CLIENT_ID")
CLIENT_SECRET=os.getenv("AMADEUS_CLIENT_SECRET")

amadeus = Client(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
)

@api_view(['GET'])
def get_flight_offers(request):
    try:
        data = request.data 

        # get all the flight data from the request
        # TODO: validate data instead of using default - return error if required fields are invalid; add more filters to the request
        origin = data.get("originLocationCode", "BUH")
        destination = data.get("destinationLocationCode", "FRA")
        departure_date = data.get("departureDate", "2025-03-15")
        adults = data.get("adults", 1)
        currency = data.get("currencyCode", "EUR")
        max_results = data.get("max", 5)
        travel_class = data.get("travelClass", "BUSINESS")
        
        # amadeus API call to fetch all flights fitting the data received
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=departure_date,
            adults=adults,
            currencyCode=currency,
            max=max_results,
            travelClass=travel_class,
        )

        flight_offers = []

        # create an array of objects containing data about each flight found
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
        
        return JsonResponse(flight_offers, safe=False, json_dumps_params={'indent': 2})

    except ResponseError as error:
        return JsonResponse({"error": str(error)}, status=400)