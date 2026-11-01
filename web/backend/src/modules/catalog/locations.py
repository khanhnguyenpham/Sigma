"""Illustrative warehouse locations, never observed delivery or sales locations."""

from core.errors import DomainError


COUNTRY_CITIES = {
    "Australia": "Sydney", "Cambodia": "Phnom Penh", "China": "Shanghai",
    "Europe (EU)": "Frankfurt", "Hong Kong": "Hong Kong", "India": "Mumbai",
    "Indonesia": "Jakarta", "Japan": "Tokyo", "Laos": "Vientiane",
    "Malaysia": "Kuala Lumpur", "Philippines": "Manila", "Singapore": "Singapore",
    "South Korea": "Seoul", "Taiwan": "Taipei", "Thailand": "Bangkok",
    "UAE": "Dubai", "USA": "Los Angeles", "Vietnam": "Ho Chi Minh City",
}

# Each declared route has its own location. Singapore/Hong Kong use urban areas
# with the user's approval (CHG-081); these are not additional city states.
ROUTE_CITIES = {
    ("Australia", "Telstra"): "Melbourne",
    ("Cambodia", "Smart"): "Siem Reap",
    ("China", "China Unicom"): "Beijing",
    ("Europe (EU)", "Three"): "Paris",
    ("Europe (EU)", "Vodafone"): "Berlin",
    ("Hong Kong", "3HK"): "Kowloon",
    ("Hong Kong", "CSL"): "Sha Tin",
    ("Hong Kong", "SmarTone"): "Tsuen Wan",
    ("India", "Jio"): "New Delhi",
    ("Indonesia", "Telkomsel"): "Surabaya",
    ("Indonesia", "XL Axiata"): "Bandung",
    ("Japan", "SoftBank"): "Osaka",
    ("Japan", "au (KDDI)"): "Kyoto",
    ("Laos", "Unitel"): "Luang Prabang",
    ("Malaysia", "Maxis"): "George Town",
    ("Malaysia", "U Mobile"): "Johor Bahru",
    ("Philippines", "Smart PH"): "Cebu City",
    ("Singapore", "M1"): "Tampines",
    ("Singapore", "Singtel"): "Jurong East",
    ("Singapore", "StarHub"): "Woodlands",
    ("South Korea", "LG U+"): "Busan",
    ("South Korea", "SKT"): "Incheon",
    ("Taiwan", "FarEasTone"): "Kaohsiung",
    ("Taiwan", "Taiwan Mobile"): "Taichung",
    ("Thailand", "TrueMove H"): "Chiang Mai",
    ("Thailand", "dtac"): "Phuket City",
    ("UAE", "du"): "Abu Dhabi",
    ("USA", "T-Mobile"): "New York City",
    ("Vietnam", "Viettel"): "Hanoi",
    ("Vietnam", "Vinaphone"): "Da Nang",
}


def seed_cities(routes):
    cities = {route: ROUTE_CITIES.get(route, COUNTRY_CITIES.get(route[0])) for route in routes}
    if None in cities.values() or len(set(cities.values())) != len(cities):
        raise DomainError("missing_partner_config", "Declare a distinct warehouse location for each route")
    return cities


def display_warehouse(warehouse):
    """Apply only the declared legacy seed rename in a copy of the read model.

    Frozen configuration/hashes remain untouched; custom and unknown locations
    keep their frozen labels, regardless of later live catalog edits.
    """
    route = (warehouse["destination_country"], warehouse["carrier"])
    if warehouse.get("is_assumed") and warehouse["city"] == COUNTRY_CITIES.get(route[0]):
        return {**warehouse, "city": ROUTE_CITIES.get(route, warehouse["city"])}
    return warehouse
