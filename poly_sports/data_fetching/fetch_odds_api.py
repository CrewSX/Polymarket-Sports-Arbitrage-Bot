"""The Odds API client for fetching sportsbook odds."""
import os
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base URL for The Odds API
ODDS_API_BASE_URL = 'https://api.the-odds-api.com'


def fetch_sports_list(api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch list of available sports from The Odds API.
    
    This endpoint does not count against the usage quota.
    
    Args:
        api_key: The Odds API key. If None, reads from ODDS_API_KEY environment variable.
        
    Returns:
        List of sport dictionaries with keys: key, group, title, description, active, has_outrights
        
    Raises:
        requests.exceptions.RequestException: If API request fails
    """
    if api_key is None:
        api_key = os.getenv('ODDS_API_KEY')
        if not api_key:
            raise ValueError("ODDS_API_KEY not provided and not found in environment variables")
    
    url = f"{ODDS_API_BASE_URL}/v4/sports"
    params = {'apiKey': api_key}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(f"Error fetching sports list: {e}")


def fetch_events(
    sport_key: str,
    api_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch events for a specific sport from The Odds API (without odds).
    
    This endpoint returns event metadata (teams, dates, IDs) without odds data.
    Use this for event matching, then fetch odds separately using fetch_odds().
    
    Args:
        sport_key: The Odds API sport key (e.g., 'americanfootball_nfl')
        api_key: The Odds API key. If None, reads from ODDS_API_KEY environment variable.
        
    Returns:
        List of event dictionaries with event metadata (id, home_team, away_team, commence_time, etc.)
        but without bookmakers/odds data
        
    Raises:
        requests.exceptions.RequestException: If API request fails
    """
    if api_key is None:
        api_key = os.getenv('ODDS_API_KEY')
        if not api_key:
            raise ValueError("ODDS_API_KEY not provided and not found in environment variables")
    
    url = f"{ODDS_API_BASE_URL}/v4/sports/{sport_key}/events"
    params = {'apiKey': api_key}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(f"Error fetching events for {sport_key}: {e}")


def fetch_odds(
    sport_key: str,
    api_key: Optional[str] = None,
    regions: List[str] = None,
    markets: List[str] = None,
    odds_format: str = 'american'
) -> List[Dict[str, Any]]:
    """
    Fetch odds for a specific sport from The Odds API.
    
    Args:
        sport_key: The Odds API sport key (e.g., 'americanfootball_nfl')
        api_key: The Odds API key. If None, reads from ODDS_API_KEY environment variable.
        regions: List of regions to fetch odds from (e.g., ['us', 'us2']). Default: ['us']
        markets: List of markets to fetch (e.g., ['h2h', 'spreads']). Default: ['h2h']
        odds_format: Odds format - 'american' or 'decimal'. Default: 'american'
        
    Returns:
        List of event dictionaries with odds from multiple bookmakers
        
    Raises:
        requests.exceptions.RequestException: If API request fails
    """
    if api_key is None:
        api_key = os.getenv('ODDS_API_KEY')
        if not api_key:
            raise ValueError("ODDS_API_KEY not provided and not found in environment variables")
    
    if regions is None:
        regions = ['us']
    if markets is None:
        markets = ['h2h']
    
    url = f"{ODDS_API_BASE_URL}/v4/sports/{sport_key}/odds"
    params = {
        'apiKey': api_key,
        'regions': ','.join(regions),
        'markets': ','.join(markets),
        'oddsFormat': odds_format
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(f"Error fetching odds for {sport_key}: {e}")


def fetch_event_odds(
    event_id: str,
    sport_key: str,
    api_key: Optional[str] = None,
    regions: List[str] = None,
    markets: List[str] = None,
    odds_format: str = 'american'
) -> Dict[str, Any]:
    """
    Fetch odds for a specific event from The Odds API.
    
    Args:
        event_id: The Odds API event ID
        sport_key: The Odds API sport key (e.g., 'americanfootball_nfl')
        api_key: The Odds API key. If None, reads from ODDS_API_KEY environment variable.
        regions: List of regions to fetch odds from (e.g., ['us', 'us2']). Default: ['us']
        markets: List of markets to fetch (e.g., ['h2h', 'spreads']). Default: ['h2h']
        odds_format: Odds format - 'american' or 'decimal'. Default: 'american'
        
    Returns:
        Event dictionary with odds from multiple bookmakers
        
    Raises:
        requests.exceptions.RequestException: If API request fails
    """
    if api_key is None:
        api_key = os.getenv('ODDS_API_KEY')
        if not api_key:
            raise ValueError("ODDS_API_KEY not provided and not found in environment variables")
    
    if regions is None:
        regions = ['us']
    if markets is None:
        markets = ['h2h']
    
    url = f"{ODDS_API_BASE_URL}/v4/sports/{sport_key}/events/{event_id}/odds"
    params = {
        'apiKey': api_key,
        'regions': ','.join(regions),
        'markets': ','.join(markets),
        'oddsFormat': odds_format
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(f"Error fetching event odds for {event_id}: {e}")

