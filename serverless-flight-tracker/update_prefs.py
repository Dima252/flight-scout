import json
import os
import subprocess

CONFIG_FILE = 'config.json'

def load_config():
    """Loads existing config or returns a default template."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "origin": "TLV",
        "destination": "Anywhere",
        "earliest_departure": "2026-10-01",
        "latest_return": "2026-10-31",
        "min_days": 10,
        "max_days": 14,
        "max_price_usd": 600
    }

def save_config(config_data):
    """Saves the dictionary back to config.json."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=2)
    print(f"\n✅ Successfully updated {CONFIG_FILE}!")

def ask(prompt_text, current_value, is_int=False):
    """Prompts the user, keeping the old value if they just press Enter."""
    user_input = input(f"{prompt_text} [{current_value}]: ").strip()
    
    if not user_input:
        return current_value # Keep the old value
    
    if is_int:
        try:
            return int(user_input)
        except ValueError:
            print("⚠️ Please enter a valid number. Keeping previous value.")
            return current_value
            
    return user_input

def main():
    print("✈️  Flight Agent Configuration Setup  ✈️")
    print("Press Enter to keep the current value inside the brackets.\n")
    
    config = load_config()
    
    config['origin'] = ask("Departure Airport Code", config.get('origin'))
    config['destination'] = ask("Destination (Code or 'Anywhere')", config.get('destination'))
    config['earliest_departure'] = ask("Earliest Departure (YYYY-MM-DD)", config.get('earliest_departure'))
    config['latest_return'] = ask("Latest Return (YYYY-MM-DD)", config.get('latest_return'))
    config['min_days'] = ask("Minimum Vacation Days", config.get('min_days'), is_int=True)
    config['max_days'] = ask("Maximum Vacation Days", config.get('max_days'), is_int=True)
    config['max_price_usd'] = ask("Max Price ($)", config.get('max_price_usd'), is_int=True)
    
    save_config(config)

    # Bonus: Ask to sync with GitHub automatically
    sync = input("\n🚀 Do you want to push these changes to GitHub now? (y/n) [n]: ").strip().lower()
    if sync == 'y':
        print("Pushing to GitHub...")
        subprocess.run(["git", "add", CONFIG_FILE])
        subprocess.run(["git", "commit", "-m", "chore: updated user flight preferences"])
        subprocess.run(["git", "push"])
        print("☁️  Preferences synced! The agent will use these on its next run.")

if __name__ == "__main__":
    main()