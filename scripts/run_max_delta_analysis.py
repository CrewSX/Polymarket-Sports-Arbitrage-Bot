"""Run max delta analysis to find sportsbooks with largest delta_difference."""
import argparse
from pathlib import Path
from poly_sports.processing.arbitrage_calculation import find_max_delta_by_sportsbook
from poly_sports.utils.file_utils import load_json, save_json


def main():
    """Load comparison data and run max delta analysis."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Find sportsbooks with largest delta_difference')
    parser.add_argument(
        '--odds-dir',
        type=str,
        default='data/sportsbook_data/odds/',
        help='Directory path to raw odds JSON files (default: data/sportsbook_data/odds/)'
    )
    parser.add_argument(
        '--top-n',
        type=int,
        default=50,
        help='Number of top events to return (default: 50)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/max_delta_by_sportsbook.json',
        help='Output file path (default: data/max_delta_by_sportsbook.json)'
    )
    args = parser.parse_args()
    
    # Load comparison data
    # Get project root (parent of scripts directory)
    project_root = Path(__file__).parent.parent
    data_file = project_root / 'data' / 'arbitrage_comparison.json'
    
    if not data_file.exists():
        print(f"Error: {data_file} not found")
        print("Please run fetch_odds_comparison.py first to generate the comparison data")
        return
    
    print(f"Loading comparison data from {data_file}...")
    comparison_data = load_json(str(data_file))
    
    print(f"Loaded {len(comparison_data)} comparison entries")
    print("\n" + "=" * 80)
    print("Running Max Delta Analysis by Sportsbook")
    print("=" * 80)
    
    # Resolve odds directory path
    odds_dir = project_root / args.odds_dir
    print(f"\nLoading raw odds from: {odds_dir}")
    
    # Run max delta analysis
    try:
        results = find_max_delta_by_sportsbook(
            comparison_data,
            odds_dir=str(odds_dir),
            top_n=args.top_n
        )
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    except Exception as e:
        print(f"Error running analysis: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\nFound {len(results)} events with max delta information")
    print("\n" + "=" * 80)
    
    if not results:
        print("No events found with delta information.")
        print("Check that raw odds files exist and events are properly matched.")
        return
    
    # Display top results
    print("\n\n## TOP EVENTS BY MAX DELTA DIFFERENCE")
    print("=" * 80)
    for i, event in enumerate(results[:20], 1):  # Show first 20
        max_delta = event.get('max_delta', {})
        print(f"\n{i}. Event ID: {event.get('pm_event_id', 'N/A')} | Market ID: {event.get('pm_market_id', 'N/A')}")
        print(f"   Max Delta Difference: {max_delta.get('delta_difference', 0):.4f}")
        print(f"   Sportsbook: {max_delta.get('sportsbook_title', 'N/A')} ({max_delta.get('sportsbook_name', 'N/A')})")
        print(f"   Outcome: {max_delta.get('outcome_name', 'N/A')}")
        print(f"   Polymarket Price: {max_delta.get('pm_price', 0):.4f}")
        print(f"   Sportsbook Implied Prob: {max_delta.get('sb_implied_prob', 0):.4f}")
        print(f"   Match Confidence: {event.get('match_confidence', 0):.3f}")
        print(f"   Liquidity: ${event.get('pm_event_liquidity', 0):,.2f}")
    
    if len(results) > 20:
        print(f"\n... and {len(results) - 20} more events")
    
    # Summary statistics
    print("\n\n" + "=" * 80)
    print("## SUMMARY STATISTICS")
    print("=" * 80)
    
    if results:
        deltas = [event.get('max_delta', {}).get('delta_difference', 0) for event in results]
        avg_delta = sum(deltas) / len(deltas) if deltas else 0
        max_delta = max(deltas) if deltas else 0
        min_delta = min(deltas) if deltas else 0
        
        print(f"\nDelta Difference Statistics:")
        print(f"  Average Delta: {avg_delta:.4f}")
        print(f"  Maximum Delta: {max_delta:.4f}")
        print(f"  Minimum Delta: {min_delta:.4f}")
        print(f"  Total Events: {len(results)}")
        
        # Count by sportsbook
        sportsbook_counts = {}
        for event in results:
            sb_name = event.get('max_delta', {}).get('sportsbook_title', 'Unknown')
            sportsbook_counts[sb_name] = sportsbook_counts.get(sb_name, 0) + 1
        
        print(f"\nTop Sportsbooks by Count:")
        sorted_sportsbooks = sorted(sportsbook_counts.items(), key=lambda x: x[1], reverse=True)
        for sb_name, count in sorted_sportsbooks[:10]:
            print(f"  {sb_name}: {count} events")
    
    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80)
    
    # Save results
    output_path = project_root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_json(results, str(output_path))
    print(f"\nResults saved to: {output_path}")


if __name__ == '__main__':
    main()

