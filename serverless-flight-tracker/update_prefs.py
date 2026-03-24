import json
import os
import subprocess
import tkinter as tk
from tkinter import messagebox

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

class PreferencesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("✈️ Flight Agent Configuration Setup")
        self.root.geometry("450x330")
        self.root.resizable(False, False)
        self.root.configure(padx=20, pady=20)
        
        self.config = load_config()
        self.entries = {}
        
        # Define fields
        fields = [
            ("origin", "Departure Airport Code"),
            ("destination", "Destination ('Anywhere' or code)"),
            ("earliest_departure", "Earliest Departure (YYYY-MM-DD)"),
            ("latest_return", "Latest Return (YYYY-MM-DD)"),
            ("min_days", "Minimum Vacation Days"),
            ("max_days", "Maximum Vacation Days"),
            ("max_price_usd", "Max Price ($)")
        ]
        
        # Create grid layout
        for i, (key, label_text) in enumerate(fields):
            tk.Label(root, text=label_text, font=("Arial", 12)).grid(row=i, column=0, sticky="w", pady=5)
            entry = tk.Entry(root, width=18, font=("Arial", 12))
            entry.insert(0, str(self.config.get(key, "")))
            entry.grid(row=i, column=1, sticky="e", pady=5)
            self.entries[key] = entry
            
        # GitHub Sync Checkbox
        self.sync_var = tk.BooleanVar(value=False)
        self.sync_checkbox = tk.Checkbutton(
            root, text="🚀 Push changes to GitHub on save", 
            variable=self.sync_var, font=("Arial", 12)
        )
        self.sync_checkbox.grid(row=len(fields), column=0, columnspan=2, pady=10)
        
        # Save Button
        self.save_btn = tk.Button(
            root, text="Save Settings", font=("Arial", 13, "bold"), command=self.save_settings
        )
        self.save_btn.grid(row=len(fields)+1, column=0, columnspan=2, ipadx=20, ipady=3)
        
    def save_settings(self):
        try:
            # Extract and validate inputs
            self.config["origin"] = self.entries["origin"].get().strip().upper()
            self.config["destination"] = self.entries["destination"].get().strip()
            self.config["earliest_departure"] = self.entries["earliest_departure"].get().strip()
            self.config["latest_return"] = self.entries["latest_return"].get().strip()
            
            # Numeric validations
            self.config["min_days"] = int(self.entries["min_days"].get().strip())
            self.config["max_days"] = int(self.entries["max_days"].get().strip())
            self.config["max_price_usd"] = int(self.entries["max_price_usd"].get().strip())
        except ValueError:
            messagebox.showerror("Invalid Input", "Make sure Minimum Days, Maximum Days, and Max Price are valid numbers!")
            return
            
        # Save to file
        save_config(self.config)
        
        # GitHub Sync
        if self.sync_var.get():
            try:
                subprocess.run(["git", "add", CONFIG_FILE], check=True)
                subprocess.run(["git", "commit", "-m", "chore: updated user flight preferences"], check=True)
                subprocess.run(["git", "push"], check=True)
                msg = f"Successfully updated {CONFIG_FILE} and pushed to GitHub! The agent will use these on its next run."
            except subprocess.CalledProcessError as e:
                messagebox.showerror("GitHub Sync Failed", f"Preferences saved locally, but failed to push to GitHub.\nError: {e}")
                return
        else:
            msg = f"Successfully updated {CONFIG_FILE} locally!"
            
        messagebox.showinfo("Success", msg)
        self.root.destroy()

def main():
    root = tk.Tk()
    app = PreferencesApp(root)
    
    # Bring to front (Mac specific trick)
    root.lift()
    root.attributes('-topmost', True)
    root.after(100, lambda: root.attributes('-topmost', False))
    
    root.mainloop()

if __name__ == "__main__":
    main()