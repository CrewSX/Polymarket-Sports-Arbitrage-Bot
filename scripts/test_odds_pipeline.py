"""Test the odds matching pipeline using mock NCAAF data."""
import json
from pathlib import Path
from poly_sports.data_fetching.fetch_odds_data import fetch_odds_for_polymarket_events, _enrich_bookmaker_data, _consolidate_bookmakers
from poly_sports.processing.event_matching import match_events
from poly_sports.processing.sport_detection import detect_sport_key
from poly_sports.data_fetching.fetch_sports_markets import save_to_csv
from poly_sports.utils.file_utils import load_json, save_json


def test_pipeline_with_mock_data():
    """Test the pipeline using mock NCAAF odds data."""
    # Get project root (parent of scripts directory)
    project_root = Path(__file__).parent.parent
    data_dir = project_root / 'data'
    
    print("=" * 60)
    print("Testing Odds API Integration Pipeline with Mock Data")
    print("=" * 60)
    
    # Step 1: Load Polymarket arbitrage data
    print("\n1. Loading Polymarket arbitrage data...")
    try:
        with open(data_dir / 'arbitrage_data_filtered.json', 'r', encoding='utf-8') as f:
            arbitrage_data = json.load(f)
        print(f"   Loaded {len(arbitrage_data)} Polymarket markets")
    except FileNotFoundError:
        print("   Error: data/arbitrage_data.json not found")
        return
    except json.JSONDecodeError as e:
        print(f"   Error: Invalid JSON: {e}")
        return
    
    # Step 2: Filter for NCAAF events only
    print("\n2. Filtering for NCAAF events...")
    ncaaf_events = []
    for event in arbitrage_data:
        sport_key = detect_sport_key(event)
        if sport_key == 'americanfootball_ncaaf':
            ncaaf_events.append(event)
    print(f"   Found {len(ncaaf_events)} NCAAF events in Polymarket data")
    
    if not ncaaf_events:
        print("   No NCAAF events found. Cannot proceed.")
        return
    
    # Step 3: Load mock Odds API events (without odds) for matching
    print("\n3. Loading mock Odds API events (without odds) for matching...")
    try:
        mock_events = load_json(str(data_dir / 'mock_ncaaf_events.json'))
        print(f"   Loaded {len(mock_events)} events from mock events data")
    except FileNotFoundError:
        print("   Error: data/mock_ncaaf_events.json not found")
        return
    except json.JSONDecodeError as e:
        print(f"   Error: Invalid JSON: {e}")
        return
    
    # Step 4: Match events
    print("\n4. Matching Polymarket events to Odds API events...")
    matches = match_events(ncaaf_events, mock_events, min_confidence=0.55)
    print(f"   Found {len(matches)} matches (confidence >= 0.8)")
    
    if not matches:
        print("   No matches found. Trying with lower confidence threshold...")
        matches = match_events(ncaaf_events, mock_events, min_confidence=0.6)
        print(f"   Found {len(matches)} matches (confidence >= 0.6)")
    
    if not matches:
        print("   No matches found. Cannot proceed.")
        return
    
    # Step 5: Load mock Odds API data (with odds)
    print("\n5. Loading mock Odds API odds data...")
    try:
        mock_odds_data = load_json(str(data_dir / 'mock_ncaaf.json'))
        print(f"   Loaded {len(mock_odds_data)} events with odds from mock data")
    except FileNotFoundError:
        print("   Error: data/mock_ncaaf.json not found")
        return
    except json.JSONDecodeError as e:
        print(f"   Error: Invalid JSON: {e}")
        return
    
    # Step 6: Create mapping of event_id -> odds_event (with bookmakers)
    print("\n6. Creating event ID to odds mapping...")
    odds_by_event_id = {event.get('id'): event for event in mock_odds_data}
    print(f"   Mapped {len(odds_by_event_id)} events with odds")
    
    # Step 7: Create merged comparison dataset
    print("\n7. Creating merged comparison dataset...")
    merged_data = []
    
    for match in matches:
        pm_event = match['pm_event']
        matched_event = match['odds_event']
        confidence = match['confidence']
        event_id = matched_event.get('id')
        
        # Get odds data for this event (if available)
        odds_event = odds_by_event_id.get(event_id)
        if not odds_event:
            # Event matched but no odds available yet, skip this match
            print(f"   Warning: Event {event_id} matched but no odds available, skipping")
            continue
        
        # Create merged entry
        merged_entry = {}
        
        # Add all Polymarket fields with 'pm_' prefix
        for key, value in pm_event.items():
            merged_entry[f'pm_{key}'] = value
        
        # Add Odds API metadata
        merged_entry['odds_api_event_id'] = event_id
        merged_entry['odds_api_sport_key'] = 'americanfootball_ncaaf'
        merged_entry['match_confidence'] = confidence
        
        # Enrich bookmaker data and consolidate
        enriched_bookmakers = []
        for bookmaker in odds_event.get('bookmakers', []):
            enriched_bookmaker = _enrich_bookmaker_data(bookmaker, 'american')
            enriched_bookmakers.append(enriched_bookmaker)
        
        # Consolidate bookmakers into aggregate statistics
        consolidated = _consolidate_bookmakers(enriched_bookmakers)
        merged_entry['sportsbook_count'] = consolidated['sportsbook_count']
        merged_entry['sportsbook_outcomes'] = consolidated['sportsbook_outcomes']
        
        merged_data.append(merged_entry)
    
    print(f"   Created {len(merged_data)} merged entries")
    
    # Step 8: Save results
    print("\n8. Saving comparison data...")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    json_filename = data_dir / 'arbitrage_comparison_test.json'
    save_json(merged_data, str(json_filename))
    print(f"   Saved JSON: {json_filename}")
    
    csv_filename = data_dir / 'arbitrage_comparison_test.csv'
    save_to_csv(merged_data, str(csv_filename))
    print(f"   Saved CSV: {csv_filename}")
    
    # Step 9: Print summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  Total Polymarket NCAAF events: {len(ncaaf_events)}")
    print(f"  Total Odds API events (for matching): {len(mock_events)}")
    print(f"  Total Odds API events (with odds): {len(mock_odds_data)}")
    print(f"  Successfully matched events: {len(matches)}")
    print(f"  Successfully merged with odds: {len(merged_data)}")
    if ncaaf_events:
        match_rate = len(merged_data) / len(mock_events) * 100
        print(f"  Match rate: {match_rate:.1f}%")
    
    # Print sample matches
    if merged_data:
        print("\n  Sample matches:")
        for i, entry in enumerate(merged_data[:5], 1):
            print(f"\n  Match {i}:")
            print(f"    Polymarket: {entry.get('pm_homeTeamName', 'N/A')} vs {entry.get('pm_awayTeamName', 'N/A')}")
            print(f"    Odds API Event ID: {entry.get('odds_api_event_id', 'N/A')}")
            print(f"    Confidence: {entry.get('match_confidence', 0):.3f}")
            print(f"    Sportsbook count: {entry.get('sportsbook_count', 0)}")
            if entry.get('sportsbook_outcomes'):
                for outcome in entry['sportsbook_outcomes'][:2]:  # Show first 2 outcomes
                    print(f"    {outcome.get('name', 'N/A')}: avg {outcome.get('avg_price_decimal', 0):.2f} ({outcome.get('avg_implied_probability', 0):.3f}) [range: {outcome.get('min_price_decimal', 0):.2f}-{outcome.get('max_price_decimal', 0):.2f}]")
    
    print("\n" + "=" * 60)
    print("Pipeline test completed successfully!")
    print("=" * 60)


if __name__ == '__main__':
    test_pipeline_with_mock_data()

