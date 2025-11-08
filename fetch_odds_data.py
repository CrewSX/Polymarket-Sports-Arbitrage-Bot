"""Main integration function for fetching and matching odds data."""
from typing import List, Dict, Any, Optional
from collections import defaultdict
from sport_detection import detect_sport_key
from event_matching import match_events
from fetch_odds_api import fetch_odds
from odds_utils import (
    american_to_decimal,
    decimal_to_american,
    american_to_implied_prob,
    decimal_to_implied_prob,
)


def _enrich_outcome_with_formats(outcome: Dict[str, Any], odds_format: str) -> Dict[str, Any]:
    """
    Enrich outcome with all odds formats (American, decimal, implied probability).
    
    Args:
        outcome: Outcome dictionary with 'price' field
        odds_format: Original format of the price ('american' or 'decimal')
        
    Returns:
        Enriched outcome dictionary with price_american, price_decimal, implied_probability
    """
    enriched = outcome.copy()
    price = outcome.get('price')
    
    if price is None:
        return enriched
    
    # Convert to all formats
    if odds_format == 'american':
        price_american = int(price)
        price_decimal = american_to_decimal(price_american)
        implied_prob = american_to_implied_prob(price_american)
    else:  # decimal
        price_decimal = float(price)
        price_american = decimal_to_american(price_decimal)
        implied_prob = decimal_to_implied_prob(price_decimal)
    
    enriched['price_american'] = price_american
    enriched['price_decimal'] = price_decimal
    enriched['implied_probability'] = implied_prob
    
    return enriched


def _enrich_bookmaker_data(bookmaker: Dict[str, Any], odds_format: str) -> Dict[str, Any]:
    """
    Enrich bookmaker data with formatted odds.
    
    Args:
        bookmaker: Bookmaker dictionary from The Odds API
        odds_format: Original format of the odds ('american' or 'decimal')
        
    Returns:
        Enriched bookmaker dictionary
    """
    enriched = {
        'bookmaker_key': bookmaker.get('key'),
        'bookmaker_title': bookmaker.get('title'),
        'last_update': bookmaker.get('last_update'),
        'markets': []
    }
    
    for market in bookmaker.get('markets', []):
        enriched_market = {
            'market_key': market.get('key'),
            'outcomes': []
        }
        
        for outcome in market.get('outcomes', []):
            enriched_outcome = _enrich_outcome_with_formats(outcome, odds_format)
            enriched_market['outcomes'].append(enriched_outcome)
        
        enriched['markets'].append(enriched_market)
    
    return enriched


def fetch_odds_for_polymarket_events(
    arbitrage_data: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    regions: List[str] = None,
    markets: List[str] = None,
    odds_format: str = 'american',
    min_confidence: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Fetch odds from The Odds API for Polymarket events and create merged comparison dataset.
    
    Process:
    1. Group Polymarket events by sport (using auto-detection)
    2. For each sport, fetch odds from The Odds API
    3. Match Polymarket events to The Odds API events
    4. Enrich with sportsbook odds (all formats)
    5. Return merged comparison dataset
    
    Args:
        arbitrage_data: List of Polymarket arbitrage data dictionaries
        api_key: The Odds API key. If None, reads from ODDS_API_KEY environment variable.
        regions: List of regions to fetch odds from (e.g., ['us', 'us2']). Default: ['us']
        markets: List of markets to fetch (e.g., ['h2h', 'spreads']). Default: ['h2h']
        odds_format: Odds format to request from API - 'american' or 'decimal'. Default: 'american'
        min_confidence: Minimum confidence score for matching events. Default: 0.5
        
    Returns:
        List of merged comparison dictionaries, each containing:
        - All original Polymarket fields (prefixed with 'pm_')
        - odds_api_event_id: The Odds API event ID
        - odds_api_sport_key: Detected sport key
        - match_confidence: Matching confidence score (0-1)
        - bookmakers: Array of bookmaker odds with all formats
    """
    if regions is None:
        regions = ['us']
    if markets is None:
        markets = ['h2h']
    
    # Group events by sport
    events_by_sport = defaultdict(list)
    for event in arbitrage_data:
        sport_key = detect_sport_key(event)
        if sport_key:
            events_by_sport[sport_key].append(event)
    
    merged_data = []
    
    # Process each sport
    for sport_key, pm_events in events_by_sport.items():
        try:
            # Fetch odds from The Odds API
            odds_events = fetch_odds(
                sport_key,
                api_key=api_key,
                regions=regions,
                markets=markets,
                odds_format=odds_format
            )
            
            # Match Polymarket events to Odds API events
            matches = match_events(pm_events, odds_events, min_confidence=min_confidence)
            
            # Create merged comparison dataset
            for match in matches:
                pm_event = match['pm_event']
                odds_event = match['odds_event']
                confidence = match['confidence']
                
                # Create merged entry
                merged_entry = {}
                
                # Add all Polymarket fields with 'pm_' prefix
                for key, value in pm_event.items():
                    merged_entry[f'pm_{key}'] = value
                
                # Add Odds API metadata
                merged_entry['odds_api_event_id'] = odds_event.get('id')
                merged_entry['odds_api_sport_key'] = sport_key
                merged_entry['match_confidence'] = confidence
                
                # Enrich and add bookmaker data
                merged_entry['bookmakers'] = []
                for bookmaker in odds_event.get('bookmakers', []):
                    enriched_bookmaker = _enrich_bookmaker_data(bookmaker, odds_format)
                    merged_entry['bookmakers'].append(enriched_bookmaker)
                
                merged_data.append(merged_entry)
        
        except Exception as e:
            # Log error but continue with other sports
            print(f"Error processing sport {sport_key}: {e}")
            continue
    
    return merged_data

