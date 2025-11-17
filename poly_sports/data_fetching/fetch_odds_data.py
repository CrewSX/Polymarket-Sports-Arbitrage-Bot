"""Main integration function for fetching and matching odds data."""
import traceback
from typing import List, Dict, Any, Optional
from collections import defaultdict
from poly_sports.processing.sport_detection import detect_sport_key
from poly_sports.processing.event_matching import match_events
from poly_sports.data_fetching.fetch_odds_api import fetch_events, fetch_odds
from poly_sports.utils.odds_utils import (
    american_to_decimal,
    decimal_to_american,
    american_to_implied_prob,
    decimal_to_implied_prob,
)
from poly_sports.utils.file_utils import save_json


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


def _consolidate_bookmakers(bookmakers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Consolidate bookmaker data into aggregate statistics by outcome name.
    
    Groups outcomes by name across all bookmakers and calculates:
    - Average price_decimal and implied_probability
    - Min/max price_decimal (for range)
    - Count of bookmakers offering each outcome
    
    Args:
        bookmakers: List of enriched bookmaker dictionaries
        
    Returns:
        Dictionary with:
        - sportsbook_count: Total number of bookmakers
        - sportsbook_outcomes: List of consolidated outcomes with aggregate stats
    """
    if not bookmakers:
        return {
            'sportsbook_count': 0,
            'sportsbook_outcomes': []
        }
    
    # Group outcomes by name across all bookmakers
    outcomes_by_name = defaultdict(lambda: {
        'price_decimals': [],
        'implied_probabilities': []
    })
    
    # Collect all outcomes from all bookmakers
    for bookmaker in bookmakers:
        for market in bookmaker.get('markets', []):
            for outcome in market.get('outcomes', []):
                outcome_name = outcome.get('name')
                if outcome_name and 'price_decimal' in outcome and 'implied_probability' in outcome:
                    outcomes_by_name[outcome_name]['price_decimals'].append(outcome['price_decimal'])
                    outcomes_by_name[outcome_name]['implied_probabilities'].append(outcome['implied_probability'])
    
    # Calculate aggregate statistics for each outcome
    consolidated_outcomes = []
    for outcome_name, values in outcomes_by_name.items():
        price_decimals = values['price_decimals']
        implied_probs = values['implied_probabilities']
        
        if price_decimals:  # Only include if we have data
            consolidated_outcomes.append({
                'name': outcome_name,
                'avg_price_decimal': sum(price_decimals) / len(price_decimals),
                'avg_implied_probability': sum(implied_probs) / len(implied_probs),
                'min_price_decimal': min(price_decimals),
                'max_price_decimal': max(price_decimals),
                'bookmaker_count': len(price_decimals)
            })
    
    return {
        'sportsbook_count': len(bookmakers),
        'sportsbook_outcomes': consolidated_outcomes
    }


def fetch_odds_for_polymarket_events(
    arbitrage_data: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    regions: List[str] = None,
    markets: List[str] = None,
    odds_format: str = 'american',
    min_confidence: float = 0.8
) -> List[Dict[str, Any]]:
    """
    Fetch odds from The Odds API for Polymarket events and create merged comparison dataset.
    
    Process:
    1. Group Polymarket events by sport (using auto-detection)
    2. For each sport, fetch events from The Odds API (without odds)
    3. Match Polymarket events to The Odds API events
    4. Fetch odds from The Odds API for the sport
    5. Merge matched events with odds data by matching event IDs
    6. Enrich with sportsbook odds (all formats)
    7. Return merged comparison dataset
    
    Args:
        arbitrage_data: List of Polymarket arbitrage data dictionaries
        api_key: The Odds API key. If None, reads from ODDS_API_KEY environment variable.
        regions: List of regions to fetch odds from (e.g., ['us', 'us2']). Default: ['us']
        markets: List of markets to fetch (e.g., ['h2h', 'spreads']). Default: ['h2h']
        odds_format: Odds format to request from API - 'american' or 'decimal'. Default: 'american'
        min_confidence: Minimum confidence score for matching events. Default: 0.8
        
    Returns:
        List of merged comparison dictionaries, each containing:
        - All original Polymarket fields (prefixed with 'pm_')
        - odds_api_event_id: The Odds API event ID
        - odds_api_sport_key: Detected sport key
        - match_confidence: Matching confidence score (0-1)
        - sportsbook_count: Total number of bookmakers
        - sportsbook_outcomes: Array of consolidated outcomes with aggregate stats
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
            print(f"Processing sport: {sport_key} ({len(pm_events)} Polymarket events)")
            
            # Step 1: Fetch events from The Odds API (without odds) for matching
            odds_events = fetch_events(sport_key, api_key=api_key)
            print(f"  Fetched {len(odds_events)} events from The Odds API")

            save_json(odds_events, f"data/sportsbook_data/events/{sport_key}.json")
            print(f"  Saved JSON file: data/sportsbook_data/events/{sport_key}.json")
            
            # Step 2: Match Polymarket events to Odds API events
            matches = match_events(pm_events, odds_events, min_confidence=min_confidence)
            print(f"  Found {len(matches)} matches (confidence >= {min_confidence})")
            
            
            if not matches:
                # No matches found, skip to next sport
                print(f"  Skipping {sport_key}: No matches found")
                continue
            
            # Step 3: Fetch odds from The Odds API for the sport
            odds_with_bookmakers = fetch_odds(
                sport_key,
                api_key=api_key,
                regions=regions,
                markets=markets,
                odds_format=odds_format
            )
            print(f"  Fetched odds for {len(odds_with_bookmakers)} events")
            save_json(odds_with_bookmakers, f"data/sportsbook_data/odds/{sport_key}.json")
            print(f"  Saved JSON file: data/sportsbook_data/odds/{sport_key}.json")
            
            # Step 4: Create a mapping of event_id -> odds_event (with bookmakers)
            odds_by_event_id = {event.get('id'): event for event in odds_with_bookmakers}
            
            # Step 5: Create merged comparison dataset
            for match in matches:
                pm_event = match['pm_event']
                matched_event = match['odds_event']
                confidence = match['confidence']
                event_id = matched_event.get('id')
                
                # Get odds data for this event (if available)
                odds_event = odds_by_event_id.get(event_id)
                if not odds_event:
                    # Event matched but no odds available yet, skip this match
                    continue
                
                # Create merged entry
                merged_entry = {}
                
                # Add all Polymarket fields with 'pm_' prefix
                for key, value in pm_event.items():
                    merged_entry[f'pm_{key}'] = value
                
                # Add Odds API metadata
                merged_entry['odds_api_event_id'] = event_id
                merged_entry['odds_api_sport_key'] = sport_key
                merged_entry['match_confidence'] = confidence
                
                # Enrich bookmaker data and consolidate
                enriched_bookmakers = []
                for bookmaker in odds_event.get('bookmakers', []):
                    enriched_bookmaker = _enrich_bookmaker_data(bookmaker, odds_format)
                    enriched_bookmakers.append(enriched_bookmaker)
                
                # Consolidate bookmakers into aggregate statistics
                consolidated = _consolidate_bookmakers(enriched_bookmakers)
                merged_entry['sportsbook_count'] = consolidated['sportsbook_count']
                merged_entry['sportsbook_outcomes'] = consolidated['sportsbook_outcomes']
                
                merged_data.append(merged_entry)
        
        except Exception as e:
            # Log error but continue with other sports
            print(f"  Error processing sport {sport_key}: {e}")
            print(f"  Traceback: {traceback.format_exc()}")
            continue
    
    return merged_data

