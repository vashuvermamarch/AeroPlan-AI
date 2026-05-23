import os 
import requests
import re
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

# Resolve absolute path to .env file in project root
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

API_KEY = os.getenv("AVIATIONSTACK_API_KEY")

def extract_iata_codes(query):
    """
    Extract departure and arrival airport IATA codes from a query string using ChatGroq.
    """
    try:
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            return "", ""
            
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=groq_api_key
        )
        prompt = f"""
        Analyze the following travel query: "{query}"
        
        Identify the departure location and the destination location mentioned.
        Then, find the 3-letter IATA airport codes for the primary airports of these locations.
        
        If no departure location is specified, leave it empty.
        If no destination is specified, leave it empty.
        
        Return ONLY a JSON object with keys "dep_iata" and "arr_iata", e.g.:
        {{"dep_iata": "JFK", "arr_iata": "MCT"}}
        
        Do not include any markdown formatting, explanations, or extra text.
        """
        response = llm.invoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        
        # Clean up any potential markdown wraps
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        data = json.loads(content.strip())
        return data.get("dep_iata", "").strip().upper(), data.get("arr_iata", "").strip().upper()
    except Exception as e:
        # Fallback will handle failure
        return "", ""

def fallback_regex_extract(query):
    """
    Simple heuristic to extract 3-letter uppercase words as airport IATA codes,
    excluding common English stop words.
    """
    codes = re.findall(r'\b[A-Z]{3}\b', query.upper())
    STOP_WORDS = {
        "FOR", "AND", "THE", "CAN", "ALL", "DAY", "OUT", "GET", "NEW", 
        "HOW", "ANY", "NOT", "BUT", "YOU", "HAS", "HAD", "ITS", "OUR", 
        "WHO", "HIM", "HER", "THEY", "THEM", "WAS", "ARE", "ONE", "TWO", 
        "SEE", "SAY", "USE", "WAY", "NOW", "OLD", "BOY", "MAN", "RUN", 
        "OFF", "AIR", "FLY", "TRIP", "OUT", "SUN", "MON", "TUE", "WED", 
        "THU", "FRI", "SAT"
    }
    filtered_codes = [c for c in codes if c not in STOP_WORDS]
    dep = filtered_codes[0] if len(filtered_codes) >= 1 else ""
    arr = filtered_codes[1] if len(filtered_codes) >= 2 else ""
    return dep, arr

def fetch_flights_from_api(params):
    """
    Perform GET request to AviationStack API and format up to 5 flight results.
    """
    url = "http://api.aviationstack.com/v1/flights"
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return []
        
        data = response.json()
        flights = []
        if "data" in data and isinstance(data["data"], list):
            for f in data['data'][:5]:
                airline = f.get("airline", {}).get("name", "Unknown")
                departure = f.get("departure", {}).get("airport", "Unknown")
                arrival = f.get("arrival", {}).get("airport", "Unknown")
                status = f.get("flight_status", "Unknown")
                flight_num = f.get("flight", {}).get("iata", "Unknown")
                flights.append(
                    f"Flight {flight_num} | Airline: {airline} | Departure: {departure} | Arrival: {arrival} | Status: {status}"
                )
        return flights
    except Exception:
        return []

def search_flights(query):
    # 1. Attempt LLM IATA extraction
    dep_iata, arr_iata = extract_iata_codes(query)
    
    # 2. Fall back to regex if both are empty
    if not dep_iata and not arr_iata:
        dep_iata, arr_iata = fallback_regex_extract(query)
        
    if not dep_iata and not arr_iata:
        return "No recent flights found matching the search criteria."

    # 3. Try searching flights with both departure and arrival IATA
    params = {
        "access_key": API_KEY,
        "limit": 5
    }
    if dep_iata:
        params["dep_iata"] = dep_iata
    if arr_iata:
        params["arr_iata"] = arr_iata
        
    flights = fetch_flights_from_api(params)
    
    # 4. Self-healing fallback: If dual search yields nothing, try arrival airport only (destination)
    if not flights and dep_iata and arr_iata:
        fallback_params = {
            "access_key": API_KEY,
            "limit": 5,
            "arr_iata": arr_iata
        }
        flights = fetch_flights_from_api(fallback_params)
        
        # 5. If arrival-only search also yields nothing, try departure airport only
        if not flights:
            fallback_params = {
                "access_key": API_KEY,
                "limit": 5,
                "dep_iata": dep_iata
            }
            flights = fetch_flights_from_api(fallback_params)
            
    if not flights:
        return "No recent flights found matching the search criteria."
        
    return "\n".join(flights)