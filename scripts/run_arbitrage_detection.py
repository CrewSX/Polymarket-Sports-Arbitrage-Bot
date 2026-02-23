"""Run arbitrage detection on test data and display results."""
import argparse
import sys
from pathlib import Path

# Ensure project root is on path when running script directly
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from poly_sports.utils.logger import logger
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
    logger.info("=" * 80)
    logger.info("Running Arbitrage Detection")
    logger.info("=" * 80)
    parser.add_argument(
        '--sort-by',
        type=str,
        choices=['profit_margin', 'delta_difference'],
        default=None,
        help='Sort opportunities by field before saving (profit_margin or delta_difference)'
    )
    parser.add_argument(
        '--min-profit',
        type=float,
        default=0.02,
        metavar='PCT',
        help='Minimum profit threshold as decimal (default: 0.02 = 2%%. Detection also caps delta at 3%%)'
    )
    parser.add_argument(
        '--min-liquidity',
        type=float,
        default=1000,
        metavar='USD',
        help='Minimum liquidity in USD (default: 1000)'
    )
    args = parser.parse_args()
    
    # Load comparison data
    # Get project root (parent of scripts directory)
    project_root = Path(__file__).parent.parent
    data_file = project_root / 'data' / 'arbitrage_comparison.json'
    
    if not data_file.exists():
        logger.info(f"Error: {data_file} not found")
        logger.info("Please run test_odds_pipeline.py first to generate the comparison data")
        return
    
    logger.info(f"Loading comparison data from {data_file}...")
    comparison_data = load_json(str(data_file))
    
    logger.info(f"Loaded {len(comparison_data)} comparison entries")
    logger.info("\n" + "=" * 80)
    logger.info("Running Arbitrage Detection")
    logger.info("=" * 80)
    
    # Run arbitrage detection (default 2%%; detection caps delta at 3%%, so use <= 0.05 to see results)
    opportunities = detect_arbitrage_opportunities(
        comparison_data,
        min_profit_threshold=args.min_profit,
        min_liquidity=args.min_liquidity
    )
    
    logger.info(f"\nFound {len(opportunities)} opportunities")
    logger.info("\n" + "=" * 80)
    
    if not opportunities:
        logger.info("No arbitrage opportunities found above the threshold.")
        logger.info("Try lowering min_profit_threshold or check the data.")
        return
    
    # All opportunities are directional (traditional arbitrage not applicable)
    directional = opportunities
    
    # Sort opportunities if requested (before displaying)
    if args.sort_by:
        logger.info(f"\nSorting opportunities by {args.sort_by} (descending)...")
        directional = sort_opportunities(directional, args.sort_by)
        logger.info(f"Sorted {len(directional)} opportunities")
    
    logger.info(f"\nDirectional Opportunities: {len(directional)}")
    logger.info("\n" + "=" * 80)
    
    # Display directional opportunities
    if directional:
        logger.info("\n\n## DIRECTIONAL OPPORTUNITIES")
        logger.info("=" * 80)
        for i, opp in enumerate(directional[:10], 1):  # Show first 10
            logger.info(f"\n{i}. Event ID: {opp.get('pm_event_id', 'N/A')} | Market ID: {opp.get('pm_market_id', 'N/A')}")
            logger.info(f"   Potential Profit: {opp['profit_margin'] * 100:.2f}% (${opp['profit_margin_absolute']:.2f} on $100 stake)")
            logger.info(f"   Market Type: {opp['market_type']}")
            logger.info(f"   Match Confidence: {opp.get('match_confidence', 0):.3f}")
            logger.info(f"   Liquidity: ${opp.get('pm_liquidity', 0):,.2f}")
            logger.info(f"   Spread: {opp.get('pm_spread', 0):.3f}")
            
            logger.info("   Matched Outcomes:")
            for match in opp.get('matched_outcomes', []):
                logger.info(f"     - {match['pm_outcome']}: Buy at {match['pm_price']:.3f}, Target: {match['sb_implied_prob']:.3f}")
                logger.info(f"       Expected movement: {(match['sb_implied_prob'] - match['pm_price']) * 100:.1f} percentage points")
            
            if 'sell_points' in opp:
                logger.info("   Recommended Sell Points:")
                for sell_point in opp['sell_points']:
                    logger.info(f"     - {sell_point['description']}: {sell_point['target_price']:.3f} "
                          f"({sell_point['profit_percentage'] * 100:.1f}% profit, {sell_point['confidence']} confidence)")
        
        if len(directional) > 10:
                logger.info(f"\n... and {len(directional) - 10} more directional opportunities")
    
    # Summary statistics
    logger.info("\n\n" + "=" * 80)
    logger.info("## SUMMARY STATISTICS")
    logger.info("=" * 80)
    
    if directional:
        avg_profit = sum(opp['profit_margin'] for opp in directional) / len(directional)
        max_profit = max(opp['profit_margin'] for opp in directional)
        logger.info(f"\nDirectional Opportunities:")
        logger.info(f"  Average Potential Profit: {avg_profit * 100:.2f}%")
        logger.info(f"  Maximum Potential Profit: {max_profit * 100:.2f}%")
        logger.info(f"  Total Opportunities: {len(directional)}")
    
    logger.info("\n" + "=" * 80)
    logger.info("Analysis complete!")
    logger.info("=" * 80)
    
    save_json(directional, "./data/directional_arbitrage.json")


if __name__ == '__main__':
    main()

