"""Fetch sports market data from Polymarket using Gamma API and optionally enrich with CLOB data."""
# Suppress urllib3 OpenSSL warning (non-critical) - must be before urllib3 is imported
# This warning occurs when urllib3 v2 is used with LibreSSL instead of OpenSSL
import warnings
warnings.filterwarnings('ignore', message='.*urllib3.*OpenSSL.*')
warnings.filterwarnings('ignore', message='.*NotOpenSSLWarning.*')

import os
import json
import csv
import re
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

# Additional suppression after urllib3 is loaded
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)
except (ImportError, AttributeError):
    pass

try:
    from py_clob_client.client import ClobClient
except ImportError:
    # Handle case where py-clob-client is not installed
    ClobClient = None


# Load environment variables
load_dotenv()


def filter_sports_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter markets to only include those with category == 'Sports'.
    
    Args:
        markets: List of market dictionaries
        
    Returns:
        Filtered list of sports markets (case-insensitive)
    """
    sports_markets = []
    for market in markets:
        category = market.get('category', '')
        if category and category.lower() == 'sports':
            sports_markets.append(market)
    return sports_markets


def fetch_sports_markets(api_url: str, limit: int = 1500, series_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
    """
    Fetch all sports markets from Gamma API using events endpoint with series_id filters.
    
    Args:
        api_url: Base URL for Gamma API
        limit: Maximum number of events to fetch per request (default: 1500)
        series_ids: List of sports series IDs to filter. If None, uses default sports series IDs.
        
    Returns:
        List of sports market dictionaries with all available fields
    """
    # Default sports series IDs (from Polymarket sports page)
    if series_ids is None:
        series_ids = [
            10187, 3, 10210, 10345, 10105, 10470, 10471, 10346, 10188, 10193,
            10204, 10194, 10195, 10203, 10189, 10209, 10437, 10438, 10439, 10444,
            10443, 10312, 10313, 10314, 10365, 10366, 10355, 10238, 10240, 10243,
            10244, 10246, 10245, 10242, 10292, 10290, 10289, 10286, 10287, 10291,
            10311, 10445, 10451, 10528, 10455, 10446, 10449, 10448, 10447, 10450,
            10453, 10330, 10317, 10315, 10359, 10363, 10364, 10360, 10362, 10361
        ]
    
    all_markets = []
    
    # Use events endpoint (not events/pagination)
    url = f"{api_url}/events"
    
    # Use requests params with list to handle multiple series_id parameters
    request_params = {
        'limit': limit,
        'closed': 'false',
        'active': 'true',
        'archived': 'false',
        'order': 'startTime',
        'include_chat': 'true'
    }
    
    # Add all series_id parameters as a list (requests will format as multiple params)
    request_params['series_id'] = series_ids
    
    try:
        response = requests.get(url, params=request_params)
        response.raise_for_status()
        data = response.json()
        
        # Events endpoint returns a list directly
        if isinstance(data, list):
            events = data
        elif isinstance(data, dict):
            # Fallback: handle dict response if API changes
            events = data.get('data', [])
        else:
            events = []
        
    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(f"Error fetching markets: {e}")
    
    return events


def enrich_market_with_clob_data(client: ClobClient, market: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich a single market with CLOB data (prices, order book, spread).
    
    Args:
        client: Initialized ClobClient instance
        market: Market dictionary
        
    Returns:
        Market dictionary with added 'clob_data' field
    """
    enriched_market = market.copy()
    
    # Try to get token IDs from clobTokenIds field (list of token ID strings)
    clob_token_ids = market.get('clobTokenIds', [])
    
    # Fallback to tokens field if clobTokenIds is not available
    if not clob_token_ids:
        tokens = market.get('tokens', [])
        if tokens:
            # Extract token_id from token objects
            clob_token_ids = [token.get('token_id') for token in tokens if token.get('token_id')]
    
    if not clob_token_ids:
        return enriched_market
    
    # Use first token ID for CLOB data
    token_id = clob_token_ids[0]
    if not token_id:
        return enriched_market
    
    clob_data = {}
    
    try:
        # Get midpoint price
        midpoint_response = client.get_midpoint(token_id)
        if midpoint_response:
            clob_data['midpoint'] = midpoint_response.get('mid')
    except Exception:
        pass  # Continue if midpoint fails
    
    try:
        # Get buy price
        buy_price_response = client.get_price(token_id, side="BUY")
        if buy_price_response:
            clob_data['buy_price'] = buy_price_response.get('price')
    except Exception:
        pass  # Continue if buy price fails
    
    try:
        # Get sell price
        sell_price_response = client.get_price(token_id, side="SELL")
        if sell_price_response:
            clob_data['sell_price'] = sell_price_response.get('price')
    except Exception:
        pass  # Continue if sell price fails
    
    try:
        # Get spread
        spread_response = client.get_spread(token_id)
        if spread_response:
            clob_data['spread'] = spread_response.get('spread')
    except Exception:
        pass  # Continue if spread fails
    
    try:
        # Get order book
        order_book = client.get_order_book(token_id)
        if order_book:
            clob_data['order_book'] = {
                'bids': [{'price': str(bid.price), 'size': str(bid.size)} for bid in order_book.bids[:5]],
                'asks': [{'price': str(ask.price), 'size': str(ask.size)} for ask in order_book.asks[:5]]
            }
    except Exception:
        pass  # Continue if order book fails
    
    if clob_data:
        enriched_market['clob_data'] = clob_data
    
    return enriched_market


def enrich_markets_with_clob_data(clob_host: str, markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich multiple markets with CLOB data.
    
    Args:
        clob_host: CLOB API host URL
        markets: List of market dictionaries
        
    Returns:
        List of enriched market dictionaries
    """
    if ClobClient is None:
        raise ImportError("py-clob-client is not installed. Install it with: pip install py-clob-client")
    
    # Initialize read-only CLOB client (no auth needed)
    client = ClobClient(clob_host)
    
    enriched_markets = []
    for market in markets:
        enriched = enrich_market_with_clob_data(client, market)
        enriched_markets.append(enriched)
    
    return enriched_markets


def enrich_events_with_clob_data(clob_host: str, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enrich events by enriching markets within each event with CLOB data.
    
    Args:
        clob_host: CLOB API host URL
        events: List of event dictionaries (each containing nested markets)
        
    Returns:
        List of enriched event dictionaries with enriched markets
    """
    if ClobClient is None:
        raise ImportError("py-clob-client is not installed. Install it with: pip install py-clob-client")
    
    # Initialize read-only CLOB client (no auth needed)
    client = ClobClient(clob_host)
    
    enriched_events = []
    for event in events:
        enriched_event = event.copy()
        markets = event.get('markets', [])
        
        # Enrich each market in the event
        enriched_markets = []
        for market in markets:
            enriched_market = enrich_market_with_clob_data(client, market)
            enriched_markets.append(enriched_market)
        
        enriched_event['markets'] = enriched_markets
        enriched_events.append(enriched_event)
    
    return enriched_events


def save_to_json(data: List[Dict[str, Any]], filename: str) -> None:
    """
    Save data to JSON file with pretty printing.
    
    Args:
        data: List of dictionaries to save
        filename: Output file path
    """
    output_path = Path(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def extract_arbitrage_data(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract arbitrage-relevant data from events for trading analysis.
    
    Filters out events where ended == True to focus on active/upcoming games.
    
    Extracts:
    - From events: id, endDate, active, liquidity, volume (all), homeTeamName, 
      awayTeamName, gameId, live, ended, score
    - From markets: id, liquidityNum, outcomes, outcomePrices, volumeNum (all), 
      groupItemTitle, groupItemThreshold, spread, PriceChanges, lastTradePrice, 
      bestBid, bestAsk
    - From series: id, ticker
    
    Additional useful fields for arbitrage:
    - startTime/eventDate (game timing)
    - competitive (market competitiveness)
    - volume metrics (1wk, 1mo, 1yr)
    - conditionId (market identification)
    - clobTokenIds (for trading)
    - period/elapsed (game status)
    
    Args:
        events: List of event dictionaries from Gamma API
        
    Returns:
        List of dictionaries with extracted arbitrage data, one per market.
        Only includes markets from events that have not ended.
    """
    arbitrage_data = []
    
    for event in events:
        # Filter out ended games
        ended = event.get('ended', False)
        if ended:
            continue
        
        # Extract event-level fields
        event_id = event.get('id')
        event_end_date = event.get('endDate')
        event_active = event.get('active', False)
        event_liquidity = event.get('liquidity', 0)
        event_volume = event.get('volume', 0)
        event_volume1wk = event.get('volume1wk', 0)
        event_volume1mo = event.get('volume1mo', 0)
        event_volume1yr = event.get('volume1yr', 0)
        home_team_name = event.get('homeTeamName', '')
        away_team_name = event.get('awayTeamName', '')
        game_id = event.get('gameId')
        live = event.get('live', False)
        score = event.get('score', '')
        start_time = event.get('startTime', event.get('eventDate', ''))
        event_date = event.get('eventDate', '')
        period = event.get('period', '')
        elapsed = event.get('elapsed', '')
        competitive = event.get('competitive', 0)
        
        # Extract series information
        series_list = event.get('series', [])
        series_id = None
        series_ticker = None
        if series_list and len(series_list) > 0:
            series_id = series_list[0].get('id')
            series_ticker = series_list[0].get('ticker', '')
        
        # Extract market-level fields
        markets = event.get('markets', [])
        
        for market in markets:
            market_data = {
                # Event fields
                'event_id': event_id,
                'event_endDate': event_end_date,
                'event_active': event_active,
                'event_liquidity': event_liquidity,
                'event_volume': event_volume,
                'event_volume1wk': event_volume1wk,
                'event_volume1mo': event_volume1mo,
                'event_volume1yr': event_volume1yr,
                'homeTeamName': home_team_name,
                'awayTeamName': away_team_name,
                'gameId': game_id,
                'live': live,
                'ended': ended,
                'score': score,
                'startTime': start_time,
                'eventDate': event_date,
                'period': period,
                'elapsed': elapsed,
                'competitive': competitive,
                
                # Series fields
                'series_id': series_id,
                'series_ticker': series_ticker,
                
                # Market fields
                'market_id': market.get('id'),
                'market_liquidityNum': market.get('liquidityNum', 0),
                'market_outcomes': market.get('outcomes', ''),
                'market_outcomePrices': market.get('outcomePrices', ''),
                'market_volumeNum': market.get('volumeNum', 0),
                'market_volume1wk': market.get('volume1wk', 0),
                'market_volume1mo': market.get('volume1mo', 0),
                'market_volume1yr': market.get('volume1yr', 0),
                'market_volumeClob': market.get('volumeClob', 0),
                'groupItemTitle': market.get('groupItemTitle', ''),
                'groupItemThreshold': market.get('groupItemThreshold', ''),
                'spread': market.get('spread'),
                'oneDayPriceChange': market.get('oneDayPriceChange'),
                'oneHourPriceChange': market.get('oneHourPriceChange'),
                'oneWeekPriceChange': market.get('oneWeekPriceChange'),
                'lastTradePrice': market.get('lastTradePrice'),
                'bestBid': market.get('bestBid'),
                'bestAsk': market.get('bestAsk'),
                
                # Additional useful fields
                'question': market.get('question', ''),
                'conditionId': market.get('conditionId', ''),
                'clobTokenIds': market.get('clobTokenIds', ''),
                'market_active': market.get('active', False),
                'market_closed': market.get('closed', False),
                'market_endDate': market.get('endDate', ''),
                'market_endDateIso': market.get('endDateIso', ''),
                'liquidityClob': market.get('liquidityClob', 0),
                'acceptingOrders': market.get('acceptingOrders', False),
            }
            
            arbitrage_data.append(market_data)
    
    return arbitrage_data


def filter_match_winner_and_draw_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter arbitrage markets to only include match winner and draw markets.
    
    Includes:
    - Match winner markets: Markets where outcomes contain team names (not "Over"/"Under"/"Yes"/"No")
    - Match winner markets (three-way split): Markets where outcomes = ["Yes", "No"] AND 
      question contains "Will [team] win" pattern
    - Draw markets: Markets where groupItemTitle contains "Draw" OR question contains "end in a draw"
    
    Excludes:
    - Over/Under markets: Outcomes contain ["Over", "Under"] OR groupItemTitle/question contains "O/U" or "Over/Under"
    - Both Teams to Score: Outcomes = ["Yes", "No"] AND (groupItemTitle/question contains "Both Teams to Score")
    - Spread markets: groupItemTitle matches pattern like "Team (-X.X)" OR question contains "Spread:"
    
    Args:
        markets: List of arbitrage market dictionaries
        
    Returns:
        Filtered list containing only match winner and draw markets
    """
    filtered_markets = []
    
    # Standard exclusion keywords
    EXCLUSION_KEYWORDS = {
        'over_under': ['o/u', 'over/under', 'over under'],
        'both_teams': ['both teams to score'],
        'spread': ['spread:']
    }
    
    for market in markets:
        # Parse market_outcomes JSON string
        market_outcomes_str = market.get('market_outcomes', '')
        try:
            if market_outcomes_str:
                outcomes = json.loads(market_outcomes_str)
            else:
                outcomes = []
        except (json.JSONDecodeError, TypeError):
            outcomes = []
        
        # Get text fields for pattern matching (case-insensitive)
        group_item_title = market.get('groupItemTitle', '').lower()
        question = market.get('question', '').lower()
        
        # Check exclusions first
        
        # Exclude Over/Under markets
        if outcomes == ['Over', 'Under']:
            continue
        if any(keyword in group_item_title or keyword in question 
               for keyword in EXCLUSION_KEYWORDS['over_under']):
            continue
        
        # Exclude Both Teams to Score markets
        if outcomes == ['Yes', 'No']:
            if any(keyword in group_item_title or keyword in question 
                   for keyword in EXCLUSION_KEYWORDS['both_teams']):
                continue
        
        # Exclude Spread markets
        # Check for spread pattern in groupItemTitle: "Team Name (-X.X)" or similar
        spread_pattern = r'\(-?\d+\.?\d*\)'
        if re.search(spread_pattern, group_item_title):
            continue
        if any(keyword in question for keyword in EXCLUSION_KEYWORDS['spread']):
            continue
        
        # Now check for inclusions
        
        # Include Draw markets
        if 'draw' in group_item_title or 'end in a draw' in question:
            filtered_markets.append(market)
            continue
        
        # Include match winner markets with team names in outcomes
        # Check if outcomes contain team names (not standard betting terms)
        standard_betting_terms = {'over', 'under', 'yes', 'no', 'draw'}
        if outcomes and all(
            outcome.lower() not in standard_betting_terms 
            for outcome in outcomes
        ):
            # This looks like team names, include it
            filtered_markets.append(market)
            continue
        
        # Include match winner markets (three-way split) with "Will [team] win" pattern
        if outcomes == ['Yes', 'No']:
            # Check if question matches "Will [team] win" pattern
            will_win_pattern = r'will\s+.+\s+win'
            if re.search(will_win_pattern, question, re.IGNORECASE):
                filtered_markets.append(market)
                continue
    
    return filtered_markets


def filter_arbitrage_json(input_file: str, output_dir: str = 'data') -> None:
    """
    Filter arbitrage data JSON file to only include match winner and draw markets.
    
    Args:
        input_file: Path to input arbitrage_data.json file
        output_dir: Directory to save filtered output files
    """
    print(f"Loading arbitrage data from {input_file}...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            markets = json.load(f)
    except FileNotFoundError:
        print(f"Error: File {input_file} not found")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {input_file}: {e}")
        return
    
    print(f"Loaded {len(markets)} markets")
    
    # Apply filter
    print("Filtering for match winner and draw markets...")
    filtered_markets = filter_match_winner_and_draw_markets(markets)
    print(f"Filtered to {len(filtered_markets)} markets")
    
    # Save filtered results
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    json_filename = output_path / 'arbitrage_data_filtered.json'
    print(f"Saving filtered data to {json_filename}...")
    save_to_json(filtered_markets, str(json_filename))
    
    csv_filename = output_path / 'arbitrage_data_filtered.csv'
    print(f"Saving filtered data to {csv_filename}...")
    save_to_csv(filtered_markets, str(csv_filename))
    
    # Print summary statistics
    print(f"\nSummary:")
    print(f"  Total markets loaded: {len(markets)}")
    print(f"  Filtered markets: {len(filtered_markets)}")
    print(f"  Excluded markets: {len(markets) - len(filtered_markets)}")
    print(f"  Filtered JSON: {json_filename}")
    print(f"  Filtered CSV: {csv_filename}")


def save_to_csv(data: List[Dict[str, Any]], filename: str) -> None:
    """
    Save data to CSV file, flattening nested structures.
    
    Args:
        data: List of dictionaries to save
        filename: Output file path
    """
    if not data:
        # Create empty CSV with headers if possible
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            f.write('')  # Empty file
        return
    
    output_path = Path(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Flatten nested structures
    flattened_data = []
    for item in data:
        flattened = {}
        for key, value in item.items():
            if isinstance(value, (dict, list)):
                # Serialize nested structures as JSON strings
                flattened[key] = json.dumps(value)
            else:
                flattened[key] = value
        flattened_data.append(flattened)
    
    # Get all unique keys from all items
    all_keys = set()
    for item in flattened_data:
        all_keys.update(item.keys())
    
    # Write CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
        writer.writeheader()
        for item in flattened_data:
            # Fill missing keys with empty strings
            row = {key: item.get(key, '') for key in all_keys}
            writer.writerow(row)


def main() -> None:
    """Main execution function."""
    # Load configuration from environment
    gamma_api_url = os.getenv('GAMMA_API_URL', 'https://gamma-api.polymarket.com')
    clob_host = os.getenv('CLOB_HOST', 'https://clob.polymarket.com')
    enrich_with_clob = os.getenv('ENRICH_WITH_CLOB', 'false').lower() == 'true'
    output_dir = os.getenv('OUTPUT_DIR', 'data')
    
    print(f"Fetching sports markets from {gamma_api_url}...")
    
    # Fetch sports markets using events endpoint with sports series IDs
    try:
        events = fetch_sports_markets(gamma_api_url, limit=1500)
        print(f"Found {len(events)} sports events")
    except Exception as e:
        print(f"Error fetching markets: {e}")
        return
    
    # Extract arbitrage-relevant data
    print("Extracting arbitrage data...")
    arbitrage_data = extract_arbitrage_data(events)
    print(f"Extracted {len(arbitrage_data)} markets for arbitrage analysis")
    
    # Optionally enrich with CLOB data
    if enrich_with_clob:
        print("Enriching markets with CLOB data...")
        try:
            events = enrich_events_with_clob_data(clob_host, events)
            print("CLOB enrichment completed")
        except Exception as e:
            print(f"Warning: Error during CLOB enrichment: {e}")
            print("Continuing with unenriched data...")
    
    # Save full events data to JSON
    json_filename = os.path.join(output_dir, 'sports_markets.json')
    print(f"Saving full data to {json_filename}...")
    save_to_json(events, json_filename)
    
    # Save full events data to CSV
    csv_filename = os.path.join(output_dir, 'sports_markets.csv')
    print(f"Saving full data to {csv_filename}...")
    save_to_csv(events, csv_filename)
    
    # Save arbitrage data to JSON
    arbitrage_json_filename = os.path.join(output_dir, 'arbitrage_data.json')
    print(f"Saving arbitrage data to {arbitrage_json_filename}...")
    save_to_json(arbitrage_data, arbitrage_json_filename)
    
    # Save arbitrage data to CSV
    arbitrage_csv_filename = os.path.join(output_dir, 'arbitrage_data.csv')
    print(f"Saving arbitrage data to {arbitrage_csv_filename}...")
    save_to_csv(arbitrage_data, arbitrage_csv_filename)
    
    # Print summary
    print(f"\nSummary:")
    print(f"  Total sports events: {len(events)}")
    print(f"  Total markets for arbitrage: {len(arbitrage_data)}")
    print(f"  Full data JSON: {json_filename}")
    print(f"  Full data CSV: {csv_filename}")
    print(f"  Arbitrage data JSON: {arbitrage_json_filename}")
    print(f"  Arbitrage data CSV: {arbitrage_csv_filename}")
    if enrich_with_clob:
        # Count markets (not events) with CLOB data
        enriched_count = sum(
            sum(1 for market in event.get('markets', []) if 'clob_data' in market)
            for event in events
        )
        print(f"  Markets with CLOB data: {enriched_count}")


def extract_from_json_file(input_file: str, output_dir: str = 'data') -> None:
    """
    Extract arbitrage data from an existing JSON file.
    
    Args:
        input_file: Path to input JSON file with events data
        output_dir: Directory to save output files
    """
    print(f"Loading data from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        events = json.load(f)
    
    print(f"Loaded {len(events)} events")
    
    # Extract arbitrage data
    print("Extracting arbitrage data...")
    arbitrage_data = extract_arbitrage_data(events)
    print(f"Extracted {len(arbitrage_data)} markets for arbitrage analysis")
    
    # Save arbitrage data
    arbitrage_json_filename = os.path.join(output_dir, 'arbitrage_data.json')
    print(f"Saving arbitrage data to {arbitrage_json_filename}...")
    save_to_json(arbitrage_data, arbitrage_json_filename)
    
    arbitrage_csv_filename = os.path.join(output_dir, 'arbitrage_data.csv')
    print(f"Saving arbitrage data to {arbitrage_csv_filename}...")
    save_to_csv(arbitrage_data, arbitrage_csv_filename)
    
    print(f"\nSummary:")
    print(f"  Total markets for arbitrage: {len(arbitrage_data)}")
    print(f"  Arbitrage data JSON: {arbitrage_json_filename}")
    print(f"  Arbitrage data CSV: {arbitrage_csv_filename}")


if __name__ == '__main__':
    import sys
    
    # Check for filter command
    if len(sys.argv) > 1 and sys.argv[1] == 'filter':
        # Filter mode: filter existing arbitrage_data.json
        if len(sys.argv) > 2:
            input_file = sys.argv[2]
        else:
            input_file = 'data/arbitrage_data.json'
        output_dir = sys.argv[3] if len(sys.argv) > 3 else 'data'
        filter_arbitrage_json(input_file, output_dir)
    elif len(sys.argv) > 1:
        # Extract mode: extract from events JSON file
        input_file = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else 'data'
        extract_from_json_file(input_file, output_dir)
    else:
        # Default: fetch and process markets
        main()

