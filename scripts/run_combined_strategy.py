"""Run combined directional and hedging strategy."""
import argparse
import json
from pathlib import Path
from poly_sports.processing.arbitrage_calculation import (
    detect_arbitrage_opportunities,
    find_hedgeable_sportsbooks
)
from poly_sports.utils.file_utils import load_json, save_json


def main():
    """Load comparison data, find directional opportunities, and identify hedgeable sportsbooks."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run combined directional and hedging strategy')
    parser.add_argument(
        '--odds-dir',
        type=str,
        default='data/sportsbook_data/odds/',
        help='Directory path to raw odds JSON files (default: data/sportsbook_data/odds/)'
    )
    parser.add_argument(
        '--min-profit-threshold',
        type=float,
        default=0.1,
        help='Minimum profit margin threshold (default: 0.1 = 10%%)'
    )
    parser.add_argument(
        '--min-volume',
        type=float,
        default=1000,
        help='Minimum volume threshold (default: 1000)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/combined_strategy_results.json',
        help='Output file path (default: data/combined_strategy_results.json)'
    )
    args = parser.parse_args()
    
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
    print("Running Combined Directional and Hedging Strategy")
    print("=" * 80)
    
    # Run arbitrage detection to find directional opportunities
    print(f"\nFinding directional opportunities...")
    print(f"  Min profit threshold: {args.min_profit_threshold * 100:.1f}%")
    print(f"  Min volume: {args.min_volume:,.0f}")
    
    opportunities = detect_arbitrage_opportunities(
        comparison_data,
        min_profit_threshold=args.min_profit_threshold,
        min_liquidity=args.min_volume  # Using liquidity param but filtering by volume later
    )
    
    # Filter to only 2-way markets and by volume
    opportunities = [
        opp for opp in opportunities
        if opp.get('market_type') == '2-way' and (opp.get('volume') or 0) >= args.min_volume
    ]
    
    print(f"Found {len(opportunities)} directional opportunities (2-way markets only)")
    
    if not opportunities:
        print("No directional opportunities found above the threshold.")
        print("Try lowering --min-profit-threshold or --min-volume.")
        return
    
    # Load raw odds data
    odds_dir = project_root / args.odds_dir
    if not odds_dir.exists():
        print(f"Error: Odds directory not found: {odds_dir}")
        return
    
    print(f"\nLoading raw odds from: {odds_dir}")
    
    # Create mapping of event_id -> event data with bookmakers
    odds_by_event_id = {}
    for odds_file in odds_dir.glob('*.json'):
        try:
            odds_data = load_json(str(odds_file))
            if not isinstance(odds_data, list):
                continue
            
            for event in odds_data:
                event_id = event.get('id')
                if event_id:
                    odds_by_event_id[event_id] = event
        except Exception:
            continue
    
    print(f"Loaded odds for {len(odds_by_event_id)} events")
    
    # Process each opportunity to find hedgeable sportsbooks
    print("\n" + "=" * 80)
    print("Analyzing hedgeable sportsbooks for each opportunity...")
    print("=" * 80)
    
    opportunities_with_hedging = []
    
    for opp in opportunities:
        try:
            odds_api_event_id = opp.get('odds_api_event_id')
            if not odds_api_event_id:
                continue
            
            # Find matching raw odds event
            raw_odds_event = odds_by_event_id.get(odds_api_event_id)
            if not raw_odds_event or not raw_odds_event.get('bookmakers'):
                continue
            
            # Extract PM outcomes and prices from comparison data
            # We need to find the original entry to get PM outcomes/prices
            original_entry = None
            for entry in comparison_data:
                if entry.get('odds_api_event_id') == odds_api_event_id:
                    original_entry = entry
                    break
            
            if not original_entry:
                continue
            
            pm_outcomes_str = original_entry.get('pm_market_outcomes', '')
            pm_prices_str = original_entry.get('pm_market_outcomePrices', '')
            
            if not pm_outcomes_str or not pm_prices_str:
                continue
            
            # Parse JSON strings
            try:
                pm_outcomes = json.loads(pm_outcomes_str) if isinstance(pm_outcomes_str, str) else pm_outcomes_str
                pm_prices = [float(p) for p in json.loads(pm_prices_str)] if isinstance(pm_prices_str, str) else pm_prices_str
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
            
            if len(pm_outcomes) != len(pm_prices):
                continue
            
            # Find hedgeable sportsbooks
            hedgeable_sportsbooks = find_hedgeable_sportsbooks(
                opp,
                raw_odds_event,
                pm_outcomes,
                pm_prices
            )
            
            # Add hedgeable sportsbooks to opportunity
            opp_with_hedging = opp.copy()
            opp_with_hedging['hedgeable_sportsbooks'] = hedgeable_sportsbooks
            opp_with_hedging['hedgeable_count'] = len(hedgeable_sportsbooks)
            
            opportunities_with_hedging.append(opp_with_hedging)
        
        except Exception:
            # Skip opportunities that cause errors
            continue
    
    print(f"\nProcessed {len(opportunities_with_hedging)} opportunities with hedging analysis")
    
    # Sort by number of hedgeable sportsbooks (descending), then by profit margin
    opportunities_with_hedging.sort(
        key=lambda x: (x.get('hedgeable_count', 0), x.get('profit_margin', 0)),
        reverse=True
    )
    
    # Display results
    print("\n" + "=" * 80)
    print("## COMBINED STRATEGY RESULTS")
    print("=" * 80)
    
    if not opportunities_with_hedging:
        print("No opportunities found with hedgeable sportsbooks.")
        return
    
    # Show top opportunities
    for i, opp in enumerate(opportunities_with_hedging[:20], 1):  # Show first 20
        print(f"\n{i}. Event ID: {opp.get('pm_event_id', 'N/A')} | Market ID: {opp.get('pm_market_id', 'N/A')}")
        print(f"   Potential Profit: {opp['profit_margin'] * 100:.2f}% (${opp['profit_margin_absolute']:.2f} on $100 stake)")
        print(f"   Match Confidence: {opp.get('match_confidence', 0):.3f}")
        print(f"   Volume: ${opp.get('volume', 0):,.2f}")
        print(f"   Hedgeable Sportsbooks: {opp.get('hedgeable_count', 0)}")
        
        matched_outcomes = opp.get('matched_outcomes', [])
        if matched_outcomes:
            match = matched_outcomes[0]
            print(f"   Opportunity: Buy {match['pm_outcome']} at {match['pm_price']:.3f}")
            print(f"   Target: {match['sb_implied_prob']:.3f}")
        
        hedgeable = opp.get('hedgeable_sportsbooks', [])
        if hedgeable:
            print(f"   Hedgeable Sportsbooks:")
            # Sort by hedge_sum (ascending - best hedges first)
            hedgeable_sorted = sorted(hedgeable, key=lambda x: x.get('hedge_sum', 1.0))
            for hedge in hedgeable_sorted[:5]:  # Show top 5 hedges
                print(f"     - {hedge['sportsbook_title']}: Hedge sum = {hedge['hedge_sum']:.4f} "
                      f"(PM: {hedge['pm_price']:.3f} + SB: {hedge['sb_opposite_implied_prob']:.3f})")
            if len(hedgeable) > 5:
                print(f"     ... and {len(hedgeable) - 5} more sportsbooks")
    
    if len(opportunities_with_hedging) > 20:
        print(f"\n... and {len(opportunities_with_hedging) - 20} more opportunities")
    
    # Summary statistics
    print("\n\n" + "=" * 80)
    print("## SUMMARY STATISTICS")
    print("=" * 80)
    
    if opportunities_with_hedging:
        avg_profit = sum(opp['profit_margin'] for opp in opportunities_with_hedging) / len(opportunities_with_hedging)
        max_profit = max(opp['profit_margin'] for opp in opportunities_with_hedging)
        total_hedgeable = sum(opp.get('hedgeable_count', 0) for opp in opportunities_with_hedging)
        opportunities_with_hedges = sum(1 for opp in opportunities_with_hedging if opp.get('hedgeable_count', 0) > 0)
        
        print(f"\nDirectional Opportunities:")
        print(f"  Total Opportunities: {len(opportunities_with_hedging)}")
        print(f"  Average Potential Profit: {avg_profit * 100:.2f}%")
        print(f"  Maximum Potential Profit: {max_profit * 100:.2f}%")
        print(f"  Opportunities with Hedges: {opportunities_with_hedges} ({opportunities_with_hedges / len(opportunities_with_hedging) * 100:.1f}%)")
        print(f"  Total Hedgeable Sportsbooks: {total_hedgeable}")
        
        if opportunities_with_hedges > 0:
            avg_hedges = total_hedgeable / opportunities_with_hedges
            print(f"  Average Hedges per Opportunity: {avg_hedges:.1f}")
            
            # Calculate average hedge sum
            all_hedge_sums = []
            for opp in opportunities_with_hedging:
                for hedge in opp.get('hedgeable_sportsbooks', []):
                    all_hedge_sums.append(hedge.get('hedge_sum', 1.0))
            
            if all_hedge_sums:
                avg_hedge_sum = sum(all_hedge_sums) / len(all_hedge_sums)
                min_hedge_sum = min(all_hedge_sums)
                print(f"  Average Hedge Sum: {avg_hedge_sum:.4f}")
                print(f"  Best Hedge Sum: {min_hedge_sum:.4f}")
    
    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80)
    
    # Save results
    output_path = project_root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_json(opportunities_with_hedging, str(output_path))
    print(f"\nResults saved to: {output_path}")


if __name__ == '__main__':
    main()

