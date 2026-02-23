"""Fetch and merge odds data from Polymarket and The Odds API for arbitrage analysis."""
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from poly_sports.data_fetching.fetch_sports_markets import extract_arbitrage_data, fetch_sports_markets, save_to_csv
from poly_sports.utils.file_utils import save_json, load_json
from poly_sports.data_fetching.fetch_odds_data import fetch_odds_for_polymarket_events
from poly_sports.utils.logger import logger



# Load environment variables
load_dotenv()


def main() -> None:
    """Main execution function to fetch and merge odds data."""
    # Load configuration from environment
    gamma_api_url = os.getenv('GAMMA_API_URL', 'https://gamma-api.polymarket.com')
    odds_api_key = os.getenv('ODDS_API_KEY')
    odds_api_regions = os.getenv('ODDS_API_REGIONS', 'us, us_ex').split(',')
    odds_api_markets = os.getenv('ODDS_API_MARKETS', 'h2h').split(',')
    odds_api_format = os.getenv('ODDS_API_ODDS_FORMAT', 'american')
    output_dir = os.getenv('OUTPUT_DIR', 'data')
    min_confidence = float(os.getenv('ODDS_API_MIN_CONFIDENCE', '0.8'))
    exclude_1h_moneyline = os.getenv('EXCLUDE_1H_MONEYLINE', 'false').lower() == 'true'
    use_stored_events = os.getenv('USE_STORED_EVENTS', 'true').lower() == 'true'
    events_dir = os.getenv('EVENTS_DIR', 'data/sportsbook_data/events')
    
    if not odds_api_key:
        logger.info("Error: ODDS_API_KEY not found in environment variables")
        logger.info("Please set ODDS_API_KEY in your .env file")
        return
    
    logger.info(f"Fetching sports markets from {gamma_api_url}...")
    
    # Step 1: Fetch Polymarket sports markets
    try:
        events = fetch_sports_markets(gamma_api_url, limit=1500)
        logger.info(f"Found {len(events)} sports events")
    except Exception as e:
        logger.info(f"Error fetching markets: {e}")
        return
    
    # Step 2: Extract arbitrage data
    logger.info("Extracting arbitrage data...")
    if exclude_1h_moneyline:
        logger.info("  Excluding 1h moneyline bets")
    arbitrage_data = extract_arbitrage_data(events, exclude_1h_moneyline=exclude_1h_moneyline)
    logger.info(f"Extracted {len(arbitrage_data)} markets for arbitrage analysis")
    
    arbitrage_data = load_json("data/arbitrage_data_filtered.json")

    if not arbitrage_data:
        logger.info("No arbitrage data found. Exiting.")
        return
    
    # Step 3: Fetch and merge odds from The Odds API
    logger.info(f"Fetching odds from The Odds API for {len(arbitrage_data)} events...") 
    logger.info(f"  Regions: {odds_api_regions}")
    logger.info(f"  Markets: {odds_api_markets}")
    logger.info(f"  Format: {odds_api_format}")
    logger.info(f"  Min confidence: {min_confidence}")
    logger.info(f"  Use stored events: {use_stored_events}")
    if use_stored_events:
        logger.info(f"  Events directory: {events_dir}")
    
    try:
        comparison_data = fetch_odds_for_polymarket_events(
            arbitrage_data,
            api_key=odds_api_key,
            regions=odds_api_regions,
            markets=odds_api_markets,
            odds_format=odds_api_format,
            min_confidence=min_confidence,
            use_stored_events=use_stored_events,
            events_dir=events_dir
        )
        logger.info(f"Successfully matched {len(comparison_data)} events with sportsbook odds")
    except Exception as e:
        logger.info(f"Error fetching odds: {e}")
        return
    
    # Step 4: Save comparison data
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    json_filename = output_path / 'arbitrage_comparison.json'
    logger.info(f"Saving comparison data to {json_filename}...")
    save_json(comparison_data, str(json_filename))
    
    csv_filename = output_path / 'arbitrage_comparison.csv'
    logger.info(f"Saving comparison data to {csv_filename}...")
    save_to_csv(comparison_data, str(csv_filename))
    
    # Print summary
    logger.info(f"\nSummary:")
    # print(f"  Total Polymarket events: {len(events)}")
    logger.info(f"  Total markets for arbitrage: {len(arbitrage_data)}")
    if exclude_1h_moneyline:
        logger.info(f"  (1h moneyline bets excluded)")
    logger.info(f"  Successfully matched events: {len(comparison_data)}")
    logger.info(f"  Match rate: {len(comparison_data)/len(arbitrage_data)*100:.1f}%")
    logger.info(f"  Comparison JSON: {json_filename}")
    logger.info(f"  Comparison CSV: {csv_filename}")
    
    # Print sample of matched events
    if comparison_data:
        logger.info(f"\nSample matched event:")
        sample = comparison_data[0]
        logger.info(f"  Polymarket: {sample.get('pm_homeTeamName', 'N/A')} vs {sample.get('pm_awayTeamName', 'N/A')}")
        logger.info(f"  Sport: {sample.get('odds_api_sport_key', 'N/A')}")
        logger.info(f"  Confidence: {sample.get('match_confidence', 0):.2f}")
        logger.info(f"  Sportsbooks: {sample.get('sportsbook_count', 0)}")


if __name__ == '__main__':
    main()

