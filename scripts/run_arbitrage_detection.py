"""Run arbitrage detection on test data and display results."""
import argparse
from pathlib import Path
from poly_sports.processing.arbitrage_calculation import detect_arbitrage_opportunities
from poly_sports.utils.file_utils import load_json, save_json


def sort_opportunities(opportunities: list, sort_by: str = None) -> list:
    """
    Sort opportunities by specified field.
    
    Args:
        opportunities: List of opportunity dictionaries
        sort_by: Field to sort by ('profit_margin' or 'delta_difference'), or None for no sorting
        
    Returns:
        Sorted list of opportunities (descending order)
    """
    if not sort_by or not opportunities:
        return opportunities
    
    valid_fields = ['profit_margin', 'delta_difference']
    if sort_by not in valid_fields:
        raise ValueError(f"sort_by must be one of {valid_fields} or None, got: {sort_by}")
    
    # Sort in descending order (highest values first)
    sorted_opps = sorted(
        opportunities,
        key=lambda x: x.get(sort_by, 0),
        reverse=True
    )
    
    return sorted_opps


def main():
    """Load test data and run arbitrage detection."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run arbitrage detection on comparison data')
    parser.add_argument(
        '--sort-by',
        type=str,
        choices=['profit_margin', 'delta_difference'],
        default=None,
        help='Sort opportunities by field before saving (profit_margin or delta_difference)'
    )
    args = parser.parse_args()
    
    # Load comparison data
    # Get project root (parent of scripts directory)
    project_root = Path(__file__).parent.parent
    data_file = project_root / 'data' / 'arbitrage_comparison.json'
    
    if not data_file.exists():
        print(f"Error: {data_file} not found")
        print("Please run test_odds_pipeline.py first to generate the comparison data")
        return
    
    print(f"Loading comparison data from {data_file}...")
    comparison_data = load_json(str(data_file))
    
    print(f"Loaded {len(comparison_data)} comparison entries")
    print("\n" + "=" * 80)
    print("Running Arbitrage Detection")
    print("=" * 80)
    
    # Run arbitrage detection
    opportunities = detect_arbitrage_opportunities(
        comparison_data,
        min_profit_threshold=0.1,  # 1% minimum profit
        min_liquidity=1000,
        pm_fee=0.0,
        sb_fee=0.0
    )
    
    print(f"\nFound {len(opportunities)} opportunities")
    print("\n" + "=" * 80)
    
    if not opportunities:
        print("No arbitrage opportunities found above the threshold.")
        print("Try lowering min_profit_threshold or check the data.")
        return
    
    # All opportunities are directional (traditional arbitrage not applicable)
    directional = opportunities
    
    # Sort opportunities if requested (before displaying)
    if args.sort_by:
        print(f"\nSorting opportunities by {args.sort_by} (descending)...")
        directional = sort_opportunities(directional, args.sort_by)
        print(f"Sorted {len(directional)} opportunities")
    
    print(f"\nDirectional Opportunities: {len(directional)}")
    print("\n" + "=" * 80)
    
    # Display directional opportunities
    if directional:
        print("\n\n## DIRECTIONAL OPPORTUNITIES")
        print("=" * 80)
        for i, opp in enumerate(directional[:10], 1):  # Show first 10
            print(f"\n{i}. Event ID: {opp.get('pm_event_id', 'N/A')} | Market ID: {opp.get('pm_market_id', 'N/A')}")
            print(f"   Potential Profit: {opp['profit_margin'] * 100:.2f}% (${opp['profit_margin_absolute']:.2f} on $100 stake)")
            print(f"   Market Type: {opp['market_type']}")
            print(f"   Match Confidence: {opp.get('match_confidence', 0):.3f}")
            print(f"   Liquidity: ${opp.get('pm_liquidity', 0):,.2f}")
            print(f"   Spread: {opp.get('pm_spread', 0):.3f}")
            
            print("   Matched Outcomes:")
            for match in opp.get('matched_outcomes', []):
                print(f"     - {match['pm_outcome']}: Buy at {match['pm_price']:.3f}, Target: {match['sb_implied_prob']:.3f}")
                print(f"       Expected movement: {(match['sb_implied_prob'] - match['pm_price']) * 100:.1f} percentage points")
            
            if 'sell_points' in opp:
                print("   Recommended Sell Points:")
                for sell_point in opp['sell_points']:
                    print(f"     - {sell_point['description']}: {sell_point['target_price']:.3f} "
                          f"({sell_point['profit_percentage'] * 100:.1f}% profit, {sell_point['confidence']} confidence)")
        
        if len(directional) > 10:
            print(f"\n... and {len(directional) - 10} more directional opportunities")
    
    # Summary statistics
    print("\n\n" + "=" * 80)
    print("## SUMMARY STATISTICS")
    print("=" * 80)
    
    if directional:
        avg_profit = sum(opp['profit_margin'] for opp in directional) / len(directional)
        max_profit = max(opp['profit_margin'] for opp in directional)
        print(f"\nDirectional Opportunities:")
        print(f"  Average Potential Profit: {avg_profit * 100:.2f}%")
        print(f"  Maximum Potential Profit: {max_profit * 100:.2f}%")
        print(f"  Total Opportunities: {len(directional)}")
    
    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80)
    
    save_json(directional, "./data/directional_arbitrage.json")


if __name__ == '__main__':
    main()

