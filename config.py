"""
Configuration and state persistence for Trading Alert Server.
Stores last known colors for each exchange to detect changes.
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

# Config file path
# Stores state.json in the same directory as the script
CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / 'state.json'


def load_state() -> Dict:
    """
    Load saved state from config file.
    """
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    # Default state
    return {
        "binance": {"color": None, "last_check": None},
        "hyperliquid": {"color": None, "last_check": None}
    }


def save_state(state: Dict) -> None:
    """Save state to config file."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Error saving state: {e}")


def update_exchange_color(exchange: str, color: str, price: Optional[float] = None) -> Optional[str]:
    """
    Update color for an exchange and return previous color if changed.
    
    Args:
        exchange: Exchange name ('binance' or 'hyperliquid')
        color: New color ('orange', 'silver', or 'navy')
        price: Current price (optional)
        
    Returns:
        Previous color if it changed, None otherwise
    """
    state = load_state()
    
    previous_color = state.get(exchange, {}).get("color")
    
    exchange_data = {
        "color": color,
        "last_check": datetime.now().isoformat()
    }
    
    if price is not None:
        exchange_data["price"] = price
        
    state[exchange] = exchange_data
    
    save_state(state)
    
    if previous_color is not None and previous_color != color:
        return previous_color
    
    return None

def get_current_status() -> Dict:
    """Get current status of all exchanges."""
    state = load_state()
    return {
        "binance": state.get("binance", {}),
        "hyperliquid": state.get("hyperliquid", {})
    }
