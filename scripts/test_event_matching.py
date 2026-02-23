"""Playground script to test event matching between Polymarket and Odds API events.

This script loads an odds sport JSON file and tries to match events with
arbitrage_data_filtered.json using the event matching functions.
"""
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
from poly_sports.processing.event_matching import match_events, calculate_match_score
from poly_sports.utils.logger import logger
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

def load_json_file(file_path: Path) -> List[Dict[str, Any]]:
    """Load JSON file and return its contents."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.info(f"Error: File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.info(f"Error: Invalid JSON in {file_path}: {e}")
        raise


def display_match_summary(matches: List[Dict[str, Any]]):
    """Display a summary of matches found."""
    if not matches:
        logger.info("\n❌ No matches found!")
        return
    
    logger.info(f"\n✅ Found {len(matches)} matches:")
    logger.info("=" * 80)
    
    # Group by confidence ranges
    high_confidence = [m for m in matches if m['confidence'] >= 0.9]
    medium_confidence = [m for m in matches if 0.7 <= m['confidence'] < 0.9]
    low_confidence = [m for m in matches if m['confidence'] < 0.7]
    
    logger.info(f"\nConfidence Breakdown:")
    logger.info(f"  High (≥0.9):    {len(high_confidence)} matches")
    logger.info(f"  Medium (0.7-0.9): {len(medium_confidence)} matches")
    logger.info(f"  Low (<0.7):      {len(low_confidence)} matches")
    
    # Display top matches
    logger.info(f"\n📊 Top 10 Matches (by confidence):")
    logger.info("-" * 80)
    sorted_matches = sorted(matches, key=lambda x: x['confidence'], reverse=True)
    
    for i, match in enumerate(sorted_matches, 1):
        pm_event = match['pm_event']
        odds_event = match['odds_event']
        confidence = match['confidence']
        
        # Extract team names
        pm_home = pm_event.get('homeTeamName', '') or pm_event.get('question', '').split(' vs.')[0] if pm_event.get('question') else 'N/A'
        pm_away = pm_event.get('awayTeamName', '') or pm_event.get('question', '').split(' vs. ')[-1].split(' (')[0] if pm_event.get('question') else 'N/A'
        
        odds_home = odds_event.get('home_team', 'N/A')
        odds_away = odds_event.get('away_team', 'N/A')
        
        pm_time = pm_event.get('startTime', pm_event.get('eventDate', 'N/A'))
        odds_time = odds_event.get('commence_time', 'N/A')
        
        logger.info(f"\n{i}. Match (confidence: {confidence:.3f})")
        logger.info(f"   Polymarket:  {pm_home} vs {pm_away}")
        logger.info(f"   Odds API:    {odds_home} vs {odds_away}")
        logger.info(f"   PM Time:     {pm_time}")
        logger.info(f"   Odds Time:   {odds_time}")
        logger.info(f"   PM Event ID: {pm_event.get('event_id', 'N/A')}")
        logger.info(f"   Odds Event ID: {odds_event.get('id', 'N/A')}")


def display_detailed_match(match: Dict[str, Any]):
    """Display detailed information about a single match."""
    pm_event = match['pm_event']
    odds_event = match['odds_event']
    confidence = match['confidence']
    
    logger.info("\n" + "=" * 80)
    logger.info("DETAILED MATCH ANALYSIS")
    logger.info("=" * 80)
    
    logger.info(f"\nConfidence Score: {confidence:.4f}")
    
    logger.info("\n📋 Polymarket Event:")
    logger.info(f"  Event ID:      {pm_event.get('event_id', 'N/A')}")
    logger.info(f"  Market ID:     {pm_event.get('market_id', 'N/A')}")
    logger.info(f"  Series Ticker: {pm_event.get('series_ticker', 'N/A')}")
    logger.info(f"  Home Team:     {pm_event.get('homeTeamName', 'N/A')}")
    logger.info(f"  Away Team:     {pm_event.get('awayTeamName', 'N/A')}")
    logger.info(f"  Question:      {pm_event.get('question', 'N/A')}")
    logger.info(f"  Market Outcomes: {pm_event.get('market_outcomes', 'N/A')}")
    logger.info(f"  Start Time:    {pm_event.get('startTime', 'N/A')}")
    logger.info(f"  Event Date:    {pm_event.get('eventDate', 'N/A')}")
    
    logger.info("\n📊 Odds API Event:")
    logger.info(f"  Event ID:      {odds_event.get('id', 'N/A')}")
    logger.info(f"  Sport Key:     {odds_event.get('sport_key', 'N/A')}")
    logger.info(f"  Sport Title:   {odds_event.get('sport_title', 'N/A')}")
    logger.info(f"  Home Team:     {odds_event.get('home_team', 'N/A')}")
    logger.info(f"  Away Team:     {odds_event.get('away_team', 'N/A')}")
    logger.info(f"  Commence Time: {odds_event.get('commence_time', 'N/A')}")
    
    # Calculate individual score components
    logger.info("\n🔍 Score Breakdown:")
    team_score = calculate_match_score(pm_event, odds_event)
    logger.info(f"  Overall Score: {team_score:.4f}")
    # Note: The calculate_match_score doesn't return breakdown, but we can show the overall


def display_unmatched_odds_events(
    matches: List[Dict[str, Any]],
    all_odds_events: List[Dict[str, Any]]
):
    """Display odds events that were not matched to any Polymarket event."""
    # Get set of matched odds event IDs
    matched_odds_ids = {match['odds_event'].get('id') for match in matches if match['odds_event'].get('id')}
    
    # Find unmatched odds events
    unmatched = [
        event for event in all_odds_events
        if event.get('id') not in matched_odds_ids
    ]
    
    if not unmatched:
        logger.info("\n✅ All odds events were matched!")
        return
    
    logger.info("\n" + "=" * 80)
    logger.info(f"❌ UNMATCHED ODDS EVENTS ({len(unmatched)} total)")
    logger.info("=" * 80)
    
    for i, event in enumerate(unmatched, 1):
        logger.info(f"\n{i}. Odds Event ID: {event.get('id', 'N/A')}")
        logger.info(f"   Sport Key:     {event.get('sport_key', 'N/A')}")
        logger.info(f"   Sport Title:   {event.get('sport_title', 'N/A')}")
        logger.info(f"   Home Team:     {event.get('home_team', 'N/A')}")
        logger.info(f"   Away Team:     {event.get('away_team', 'N/A')}")
        logger.info(f"   Commence Time: {event.get('commence_time', 'N/A')}")


def test_event_matching(
    odds_file: str,
    arbitrage_file: str = None,
    min_confidence: float = 0.5,
    detailed: bool = False,
    save_results: bool = False
):
    """Test event matching between Polymarket and Odds API events.
    
    Args:
        odds_file: Path to the odds sport JSON file (e.g., basketball_nba.json)
        arbitrage_file: Path to arbitrage_data_filtered.json (default: data/arbitrage_data_filtered.json)
        min_confidence: Minimum confidence threshold for matches (default: 0.7)
        detailed: Whether to show detailed match information
        save_results: Whether to save results to a JSON file
    """
    # Get project root
    project_root = Path(__file__).parent.parent
    data_dir = project_root / 'data'
    events_dir = data_dir / 'sportsbook_data' / 'events'
    
    # Resolve file paths
    if arbitrage_file:
        arbitrage_path = Path(arbitrage_file)
    else:
        arbitrage_path = data_dir / 'arbitrage_data_filtered.json'
    
    # Handle odds file path - could be relative to events_dir or absolute
    odds_path = Path(odds_file)
    if not odds_path.is_absolute():
        # Try events directory first
        if (events_dir / odds_path).exists():
            odds_path = events_dir / odds_path
        elif odds_path.exists():
            odds_path = odds_path.resolve()
        else:
            logger.info(f"Error: Could not find odds file: {odds_file}")
            logger.info(f"  Tried: {events_dir / odds_path}")
            logger.info(f"  Tried: {odds_path.resolve()}")
            return
    
    logger.info("=" * 80)
    logger.info("EVENT MATCHING PLAYGROUND")
    logger.info("=" * 80)
    logger.info(f"\n📁 Loading files:")
    logger.info(f"  Arbitrage data: {arbitrage_path}")
    logger.info(f"  Odds events:     {odds_path}")
    
    # Load files
    logger.info("\n📥 Loading data...")
    try:
        arbitrage_data = load_json_file(arbitrage_path)
        odds_data = load_json_file(odds_path)
        logger.info(f"  ✅ Loaded {len(arbitrage_data)} Polymarket events")
        logger.info(f"  ✅ Loaded {len(odds_data)} Odds API events")
    except Exception as e:
        logger.info(f"  ❌ Error loading files: {e}")
        return
    
    if not arbitrage_data:
        logger.info("  ❌ No Polymarket events found in arbitrage data")
        return
    
    if not odds_data:
        logger.info("  ❌ No Odds API events found")
        return
    
    # Perform matching
    logger.info(f"\n🔍 Matching events (min confidence: {min_confidence})...")
    matches = match_events(arbitrage_data, odds_data, min_confidence=min_confidence)
    
    # Display results
    display_match_summary(matches)
    
    # Show detailed information if requested
    if detailed and matches:
        logger.info("\n" + "=" * 80)
        logger.info("DETAILED MATCH INFORMATION")
        logger.info("=" * 80)
        sorted_matches = sorted(matches, key=lambda x: x['confidence'], reverse=True)
        for i, match in enumerate(sorted_matches[:5], 1):  # Show top 5
            logger.info(f"\n--- Match {i} ---")
            display_detailed_match(match)
    
    # Save results if requested
    if save_results:
        output_file = data_dir / f"matching_results_{odds_path.stem}.json"
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(matches, f, indent=2, ensure_ascii=False)
            logger.info(f"\n💾 Results saved to: {output_file}")
        except Exception as e:
            logger.info(f"\n❌ Error saving results: {e}")
    
    # Display unmatched odds events
    display_unmatched_odds_events(matches, odds_data)
    
    logger.info("\n" + "=" * 80)
    logger.info("Matching test completed!")
    logger.info("=" * 80)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Test event matching between Polymarket and Odds API events',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with basketball_nba.json
  python scripts/test_event_matching.py basketball_nba.json
  
  # Test with custom confidence threshold
  python scripts/test_event_matching.py basketball_nba.json --min-confidence 0.8
  
  # Show detailed match information
  python scripts/test_event_matching.py basketball_nba.json --detailed
  
  # Save results to file
  python scripts/test_event_matching.py basketball_nba.json --save
        """
    )
    
    parser.add_argument(
        'odds_file',
        type=str,
        help='Path to the odds sport JSON file (e.g., basketball_nba.json or data/sportsbook_data/events/basketball_nba.json)'
    )
    
    parser.add_argument(
        '--arbitrage-file',
        type=str,
        default=None,
        help='Path to arbitrage_data_filtered.json (default: data/arbitrage_data_filtered.json)'
    )
    
    parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.7,
        help='Minimum confidence threshold for matches (default: 0.7)'
    )
    
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed match information'
    )
    
    parser.add_argument(
        '--save',
        action='store_true',
        help='Save matching results to a JSON file'
    )
    
    args = parser.parse_args()
    
    test_event_matching(
        odds_file=args.odds_file,
        arbitrage_file=args.arbitrage_file,
        min_confidence=args.min_confidence,
        detailed=args.detailed,
        save_results=args.save
    )


if __name__ == '__main__':
    main()

