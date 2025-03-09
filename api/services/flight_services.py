import os
from amadeus import Client, ResponseError
from dotenv import load_dotenv
import airportsdata

load_dotenv()

CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")

amadeus = Client(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
airports = airportsdata.load('IATA')


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


def get_airport_info(airport_code):
    return airports.get(airport_code, None)
