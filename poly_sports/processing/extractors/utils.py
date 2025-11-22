"""Utility functions for team name extraction."""
import json
import unicodedata
from typing import Optional, Dict, Any, Tuple


# Transliteration mapping for common special characters in names
# Maps special characters to their ASCII equivalents
TRANSLITERATION_MAP = {
    'ł': 'l',  # Polish L with stroke
    'Ł': 'l',
    'ą': 'a',  # Polish a with ogonek
    'ć': 'c',  # Polish c with acute
    'ę': 'e',  # Polish e with ogonek
    'ń': 'n',  # Polish n with acute
    'ó': 'o',  # Polish o with acute
    'ś': 's',  # Polish s with acute
    'ź': 'z',  # Polish z with acute
    'ż': 'z',  # Polish z with dot above
    'á': 'a',  # Spanish/Portuguese a with acute
    'é': 'e',  # Spanish/Portuguese e with acute
    'í': 'i',  # Spanish/Portuguese i with acute
    'ó': 'o',  # Spanish/Portuguese o with acute
    'ú': 'u',  # Spanish/Portuguese u with acute
    'ñ': 'n',  # Spanish n with tilde
    'ü': 'u',  # German u with diaeresis
    'ö': 'o',  # German o with diaeresis
    'ä': 'a',  # German a with diaeresis
    'ß': 'ss', # German sharp s
}


def normalize_team_name(name: Optional[str]) -> str:
    """
    Normalize team name for comparison.
    
    - Convert to lowercase
    - Strip whitespace
    - Normalize special characters (e.g., "ł" -> "l", "é" -> "e")
    - Handle None/empty values
    
    Args:
        name: Team name string or None
        
    Returns:
        Normalized team name string
    """
    if not name:
        return ""
    
    # Convert to string, lowercase, and strip
    normalized = str(name).lower().strip()
    
    # Apply transliteration for special characters
    # This handles characters like "ł" that don't decompose with NFKD
    result = []
    for char in normalized:
        if char in TRANSLITERATION_MAP:
            result.append(TRANSLITERATION_MAP[char])
        else:
            result.append(char)
    normalized = ''.join(result)
    
    # Normalize unicode characters to handle other special characters
    # NFKD normalization decomposes characters (e.g., "é" -> "e" + combining mark)
    # Then we filter out combining marks to get ASCII-like characters
    normalized = unicodedata.normalize('NFKD', normalized)
    # Filter out combining characters (diacritics) to get base characters
    normalized = ''.join(c for c in normalized if not unicodedata.combining(c))
    
    return normalized


def extract_school_names_from_outcomes(pm_event: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract school names from market_outcomes for college football events.
    
    For college sports, market_outcomes contains the full school names
    (e.g., "Temple", "Army", "SMU Mustangs", "Boston College") which are
    more accurate than the team names alone.
    
    Args:
        pm_event: Polymarket event dictionary with market_outcomes and series_ticker
        
    Returns:
        Tuple of (home_school_name, away_school_name) or (None, None) if not applicable
    """
    # Check if this is a college football event
    series_ticker = str(pm_event.get('series_ticker', '')).lower()
    if not ('cfb' in series_ticker):
        return (None, None)
    
    # Parse market_outcomes JSON string
    market_outcomes_str = pm_event.get('market_outcomes', '')
    if not market_outcomes_str:
        return (None, None)
    
    if isinstance(market_outcomes_str, str):
        outcomes = json.loads(market_outcomes_str)
    else:
        outcomes = market_outcomes_str
    
    if not isinstance(outcomes, list) or len(outcomes) < 2:
        return (None, None)
    
    return (outcomes[0], outcomes[1])

