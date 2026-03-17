import os
import json
import requests
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

# --- 1. LOAD CONFIGURATION & STATE ---
with open('config.json', 'r') as f:
    config = json.load(f)

# If history.json doesn't exist or is empty, start with an empty list
try:
    with open('history.json', 'r') as f:
        history = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    history = []

# --- 2. SETUP SECRETS (From GitHub Actions) ---
API_KEY = os.environ.get('SERPAPI_KEY')
EMAIL_SENDER = os.environ.get('EMAIL_SENDER') # Your Gmail address
EMAIL_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
EMAIL_RECEIVER = os.environ.get('EMAIL_RECEIVER')

# --- 3. HELPER: GENERATE DATE COMBINATIONS ---
# This creates pairs of [Outbound Date, Return Date] based on your flexible rules
def get_date_pairs(start_date_str, end_date_str, min_days, max_days):
    start = datetime.strptime(start_date_str, "%Y-%m-%d")
    end = datetime.strptime(end_date_str, "%Y-%m-%d")
    pairs = []
    
    current_outbound = start
    while current_outbound <= end - timedelta(days=min_days):
        for days in range(min_days, max_days + 1):
            return_date = current_outbound + timedelta(days=days)
            if return_date <= end:
                pairs.append({
                    "outbound": current_outbound.strftime("%Y-%m-%d"),
                    "return": return_date.strftime("%Y-%m-%d")
                })
        current_outbound += timedelta(days=1)
    return pairs

# --- 4. SEARCH FLIGHTS ---
new_deals_found = []
date_pairs = get_date_pairs(config['earliest_departure'], config['latest_return'], config['min_days'], config['max_days'])

# We will just check the first 3 valid date combinations per day to save API credits
for dates in date_pairs[:3]: 
    params = {
        "engine": "google_flights",
        "departure_id": config['origin'],
        "arrival_id": config['destination'] if config['destination'] != "Anywhere" else "CDG", # Fallback to a major hub if Anywhere isn't supported
        "outbound_dates": dates['outbound'],
        "return_dates": dates['return'],
        "currency": "USD",
        "hl": "en",
        "api_key": API_KEY
    }

    response = requests.get("https://serpapi.com/search", params=params)
    results = response.json()

    # Parse the best flights from Google
    best_flights = results.get("best_flights", [])
    
    for flight in best_flights:
        price = flight.get("price", 9999)
        airline = flight["flights"][0]["airline"]
        flight_token = flight.get("flight_token", "") # Unique ID for the flight
        
        # Check if it's under budget AND we haven't seen it before
        if price <= config['max_price_usd'] and flight_token not in history:
            deal_msg = f"DEAL: {airline} | {dates['outbound']} to {dates['return']} | ${price}"
            new_deals_found.append(deal_msg)
            history.append(flight_token)

# --- 5. SEND EMAIL ALERT & SAVE STATE ---
if new_deals_found:
    print(f"Found {len(new_deals_found)} new deals! Sending email...")
    
    # Format Email
    msg = EmailMessage()
    msg['Subject'] = f"✈️ Flight Deal Alert: Found {len(new_deals_found)} new flights!"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg.set_content("\n".join(new_deals_found) + "\n\nBook via Google Flights!")

    # Send Email via Gmail SMTP
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)
        
    # Overwrite history.json with the newly found flight tokens
    with open('history.json', 'w') as f:
        json.dump(history, f, indent=2)
else:
    print("No new deals found today under the target price.")