"""
Configuration and state persistence for Trading Alert Server.
Stores configured assets and their last known states.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Config file path
CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / 'state.json'
DEFAULT_ASSETS = [
    {"exchange": "binance", "symbol": "BTC/USDT"},
    {"exchange": "hyperliquid", "symbol": "HYPE/USDC:USDC"}
]

def load_data() -> Dict:
    """Load all data (assets and state) from json."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure assets key exists
                if "assets" not in data:
                    data["assets"] = DEFAULT_ASSETS
                if "state" not in data:
                    data["state"] = {}
                return data
        except (json.JSONDecodeError, IOError):
            pass
    
    return {
        "assets": DEFAULT_ASSETS,
        "state": {}
    }

def save_data(data: Dict) -> None:
    """Save data to json."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving data: {e}")

def get_assets() -> List[Dict]:
    """Get list of configured assets."""
    data = load_data()
    return data["assets"]

def add_asset(exchange: str, symbol: str) -> None:
    """Add a new asset."""
    data = load_data()
    # Check if already exists
    for asset in data["assets"]:
        if asset["exchange"] == exchange and asset["symbol"] == symbol:
            return
    
    data["assets"].append({"exchange": exchange, "symbol": symbol})
    save_data(data)

def remove_asset(exchange: str, symbol: str) -> None:
    """Remove an asset."""
    data = load_data()
    data["assets"] = [
        a for a in data["assets"] 
        if not (a["exchange"] == exchange and a["symbol"] == symbol)
    ]
    # Also clean up state
    key = f"{exchange}_{symbol}"
    if key in data["state"]:
        del data["state"][key]
        
    save_data(data)

def update_asset_state(exchange: str, symbol: str, color: str, price: float) -> Optional[str]:
    """
    Update state for an asset and return previous color if changed.
    """
    data = load_data()
    key = f"{exchange}_{symbol}"
    
    previous_color = data["state"].get(key, {}).get("color")
    
    data["state"][key] = {
        "color": color,
        "price": price,
        "last_check": datetime.now().isoformat()
    }
    
    save_data(data)
    
    if previous_color is not None and previous_color != color:
        return previous_color
    return None

def get_current_status() -> Dict:
    """Get current status/state of all assets."""
    return load_data()["state"]
