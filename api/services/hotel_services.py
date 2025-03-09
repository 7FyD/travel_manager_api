from .flight_services import get_airport_info


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
