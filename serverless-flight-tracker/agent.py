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
API_KEY = os.environ.get('TEQUILA_API_KEY')
EMAIL_SENDER = os.environ.get('EMAIL_SENDER') # Your Gmail address
EMAIL_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
EMAIL_RECEIVER = os.environ.get('EMAIL_RECEIVER')

# --- 3. HELPER: GENERATE DATE RANGES ---
# Kiwi Tequila API expects format DD/MM/YYYY and search windows
def get_departure_range(start_date_str, end_date_str, min_days):
    start = datetime.strptime(start_date_str, "%Y-%m-%d")
    end = datetime.strptime(end_date_str, "%Y-%m-%d")
    # The latest departure is the end date minus the minimum vacation days
    latest_departure = end - timedelta(days=min_days)
    
    return start.strftime("%d/%m/%Y"), latest_departure.strftime("%d/%m/%Y")

# --- 4. SEARCH FLIGHTS ---
new_deals_found = []

date_from, date_to = get_departure_range(config['earliest_departure'], config['latest_return'], config['min_days'])
print(f"Searching flights departing between {date_from} and {date_to}...")

params = {
    "fly_from": config['origin'],
    "date_from": date_from,
    "date_to": date_to,
    "nights_in_dst_from": config['min_days'],
    "nights_in_dst_to": config['max_days'],
    "flight_type": "round",
    "curr": "USD",
    "price_to": config['max_price_usd'],
    "max_stopovers": 2, # Cap stopovers to avoid highly extreme flights
}

if config['destination'].lower() != "anywhere":
    params["fly_to"] = config['destination']

headers = {
    "apikey": API_KEY
}

try:
    if not API_KEY:
        print("Warning: TEQUILA_API_KEY is missing! The request will likely fail.")
        
    response = requests.get("https://api.tequila.kiwi.com/v2/search", headers=headers, params=params)
    response.raise_for_status()
    results = response.json().get('data', [])
    
    for flight in results:
        price = flight.get('price', 9999)
        airline = flight.get('airlines', ['Unknown'])[0]
        destination = flight.get('cityTo', 'Unknown')
        
        # Parse Dates
        out_date = flight['route'][0]['local_departure'].split('T')[0]
        ret_date = flight['route'][-1]['local_arrival'].split('T')[0]
        
        flight_token = flight.get('id', f"{out_date}_{ret_date}_{airline}_{price}")
        
        # Check if it's under budget AND we haven't seen it before
        if price <= config['max_price_usd'] and flight_token not in history:
            deal_msg = f"DEAL: {airline} to {destination} | {out_date} to {ret_date} | ${price}"
            new_deals_found.append(deal_msg)
            history.append(flight_token)
            
except Exception as e:
    print(f"Error scraping Tequila API: {e}")

# --- 5. SEND EMAIL ALERT & SAVE STATE ---
if new_deals_found:
    print(f"Found {len(new_deals_found)} new deals! Sending email...")
    
    # Format Email
    msg = EmailMessage()
    msg['Subject'] = f"✈️ Flight Deal Alert: Found {len(new_deals_found)} new flights!"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg.set_content("\n".join(new_deals_found) + "\n\nBook via Kiwi.com / Airlines!")

    # Send Email via Gmail SMTP
    if EMAIL_SENDER and EMAIL_PASSWORD:
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
                smtp.send_message(msg)
        except Exception as e:
            print(f"Failed to send email: {e}")
    else:
        print("Skipping email sending because credentials aren't set in the local environment.")
        print(f"Would have sent:\n{msg.get_content()}")
        
    # Overwrite history.json with the newly found flight tokens
    with open('history.json', 'w') as f:
        json.dump(history, f, indent=2)
else:
    print("No new deals found today under the target price.")