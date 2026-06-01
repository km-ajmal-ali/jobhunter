"""
Location normalization utilities.

Maps raw location strings from scraped job data to ISO 3166-1 alpha-2
country codes for structured filtering and display.
"""
from __future__ import annotations

import re

import pycountry

# US state name -> code mapping
US_STATES: dict[str, str] = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}

# US state abbreviation -> country code (used when location ends with a state code)
US_STATE_ABBREVS: set[str] = set(US_STATES.values())

# Canadian province/territory abbreviation -> country code
CA_PROVINCES: dict[str, str] = {
    "alberta": "AB", "british columbia": "BC", "manitoba": "MB",
    "new brunswick": "NB", "newfoundland and labrador": "NL",
    "nova scotia": "NS", "ontario": "ON", "prince edward island": "PE",
    "quebec": "QC", "saskatchewan": "SK",
    "nunavut": "NU", "northwest territories": "NT", "yukon": "YT",
}
CA_PROVINCE_ABBREVS: set[str] = set(CA_PROVINCES.values())

# Australian state/territory abbreviations
AU_STATES: dict[str, str] = {
    "new south wales": "NSW", "queensland": "QLD", "south australia": "SA",
    "tasmania": "TAS", "victoria": "VIC", "western australia": "WA",
    "australian capital territory": "ACT", "northern territory": "NT",
}

# City-only locations that are unambiguous -> country code
KNOWN_CITIES: dict[str, str] = {
    "bengaluru": "IN", "bangalore": "IN", "mumbai": "IN", "delhi": "IN",
    "pune": "IN", "hyderabad": "IN", "chennai": "IN", "gurgaon": "IN",
    "noida": "IN", "kolkata": "IN",
    "london": "GB", "manchester": "GB", "birmingham": "GB", "leeds": "GB",
    "edinburgh": "GB", "glasgow": "GB", "liverpool": "GB",
    "dublin": "IE", "cork": "IE",
    "toronto": "CA", "vancouver": "CA", "montreal": "CA", "ottawa": "CA",
    "calgary": "CA", "edmonton": "CA", "mississauga": "CA",
    "sydney": "AU", "melbourne": "AU", "brisbane": "AU", "perth": "AU",
    "auckland": "NZ", "wellington": "NZ",
    "tokyo": "JP", "osaka": "JP", "kyoto": "JP",
    "singapore": "SG",
    "hong kong": "HK",
    "seoul": "KR",
    "shanghai": "CN", "beijing": "CN", "shenzhen": "CN",
    "mexico city": "MX",
    "são paulo": "BR", "rio de janeiro": "BR",
    "berlin": "DE", "munich": "DE", "hamburg": "DE", "frankfurt": "DE",
    "paris": "FR",
    "madrid": "ES", "barcelona": "ES",
    "rome": "IT", "milan": "IT",
    "amsterdam": "NL", "rotterdam": "NL", "the hague": "NL",
    "brussels": "BE",
    "stockholm": "SE",
    "copenhagen": "DK",
    "oslo": "NO",
    "helsinki": "FI",
    "zurich": "CH", "geneva": "CH",
    "warsaw": "PL",
    "prague": "CZ",
    "budapest": "HU",
    "vienna": "AT",
    "warszawa": "PL",
    "krakow": "PL",
    "bucharest": "RO",
    "riga": "LV",
    "vilnius": "LT",
    "tallinn": "EE",
    "limassol": "CY",
    "tel aviv": "IL",
    "dubai": "AE", "abu dhabi": "AE",
    "riyadh": "SA",
    "jakarta": "ID",
    "kuala lumpur": "MY",
    "manila": "PH",
    "bangkok": "TH",
    "ho chi minh city": "VN", "hanoi": "VN",
    "lagos": "NG",
    "nairobi": "KE",
    "cape town": "ZA", "johannesburg": "ZA",
}

# Common suffix patterns like "USA", "United States", etc.
COUNTRY_ALIASES: dict[str, str] = {
    "usa": "US", "united states": "US", "united states of america": "US",
    "u.s.a.": "US", "u.s.": "US",
    "uk": "GB", "united kingdom": "GB", "england": "GB", "scotland": "GB",
    "wales": "GB", "northern ireland": "GB", "great britain": "GB",
    "uae": "AE", "united arab emirates": "AE",
}


def normalize_location(location: str | None) -> str | None:
    """
    Attempt to derive an ISO 3166-1 alpha-2 country code from a location string.

    Handles:
      - "Remote - US", "Remote - Canada" patterns
      - Location strings ending with a country name
      - US state names and abbreviations
      - Canadian province abbreviations
      - Known major cities without country context
      - Multi-country locations (returns the first match)

    Returns None if no country can be determined.
    """
    if not location or not location.strip():
        return None

    loc = location.strip()

    # Normalize whitespace and separators
    loc_split = re.split(r"[,;]\s*", loc)
    parts = [p.strip() for p in loc_split if p.strip()]

    # Check for "Remote - X" or "Remote, X" patterns
    remote_match = re.search(
        r"remote[-\s]+(us|usa|united\s?states|canada|uk|united\s?kingdom|"
        r"germany|india|ireland|australia|spain|france|netherlands|"
        r"colombia|brazil|estonia|japan|singapore|switzerland|poland|"
        r"portugal|chile|thailand)",
        loc, re.IGNORECASE,
    )
    if remote_match:
        country_name = remote_match.group(1).lower().replace(" ", "")
        alias_map = {
            "us": "US", "usa": "US", "unitedstates": "US",
            "canada": "CA", "uk": "GB", "unitedkingdom": "GB",
            "germany": "DE", "india": "IN", "ireland": "IE",
            "australia": "AU", "spain": "ES", "france": "FR",
            "netherlands": "NL", "colombia": "CO", "brazil": "BR",
            "estonia": "EE", "japan": "JP", "singapore": "SG",
            "switzerland": "CH", "poland": "PL", "portugal": "PT",
            "chile": "CL", "thailand": "TH",
        }
        code = alias_map.get(country_name)
        if code:
            return code

    # Try the last few parts for country matching
    for i in range(min(len(parts), 3)):
        candidate = parts[-(i + 1)].strip(".").strip().lower()

        # Check country aliases
        if candidate in COUNTRY_ALIASES:
            return COUNTRY_ALIASES[candidate]

        # Check exact country name via pycountry
        try:
            country = pycountry.countries.lookup(candidate)
            return country.alpha_2
        except LookupError:
            pass

        # Check if it's a US state name
        if candidate in US_STATES:
            return "US"

        # Check if it's a US state abbreviation
        if candidate.upper() in US_STATE_ABBREVS:
            return "US"

        # Check Canadian province/territory
        if candidate in CA_PROVINCES or candidate.upper() in CA_PROVINCE_ABBREVS:
            return "CA"

        # Check Australian state
        if candidate in AU_STATES:
            return "AU"

    # Check if the very first part is a known city
    if parts:
        first = parts[0].strip().lower()
        if first in KNOWN_CITIES:
            return KNOWN_CITIES[first]

    # Final fallback: scan entire string for country-level patterns
    full_lower = loc.lower()

    # Canada-specific patterns
    if re.search(r"\bcanada\b", full_lower):
        return "CA"

    # United States patterns (state names or "US" at word boundaries)
    if re.search(r"\bunited states\b", full_lower) or re.search(r"\bUSA\b", loc):
        return "US"

    # UK patterns
    if re.search(r"\bunited kingdom\b", full_lower) or re.search(r"\bUK\b", loc):
        return "GB"

    # Check "US-" prefixed location codes (like "US-Remote", "US-NYC")
    if re.search(r"\bUS[-\s]", loc):
        return "US"

    # Check "Remote" with no specific country -> US (default assumption)
    if "remote" in full_lower:
        return "US"

    return None
