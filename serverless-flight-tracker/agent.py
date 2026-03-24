import os
import json
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
from google_flight_analysis.scrape import Scrape, ScrapeObjects

new_deals_found = []
date_pairs = get_date_pairs(config['earliest_departure'], config['latest_return'], config['min_days'], config['max_days'])

print(f"Checking {len(date_pairs)} date combinations...")

# We check all valid date combinations over the period
for dates in date_pairs: 
    try:
        dest = config['destination'] if config['destination'] != "Anywhere" else "CDG"
        print(f"Scraping flights from {config['origin']} to {dest} ({dates['outbound']} -> {dates['return']})")
        
        result = Scrape(config['origin'], dest, dates['outbound'], dates['return'])
        ScrapeObjects(result)
        
        df = result.data
        if not df.empty:
            for index, row in df.iterrows():
                try:
                    price = int(row['Price'])
                    airline = str(row['Airline'])
                    # Generate a unique token since we no longer have SerpAPI's flight_token
                    flight_token = f"{dates['outbound']}_{dates['return']}_{airline}_{price}"
                    
                    if price <= config['max_price_usd'] and flight_token not in history:
                        deal_msg = f"DEAL: {airline} | {dates['outbound']} to {dates['return']} | ${price}"
                        new_deals_found.append(deal_msg)
                        history.append(flight_token)
                except (ValueError, KeyError) as e:
                    print(f"Error parsing row: {e}")
                    
    except Exception as e:
        print(f"Error scraping {dates['outbound']} to {dates['return']}: {e}")

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