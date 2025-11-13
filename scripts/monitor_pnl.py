"""Monitor real-time Polymarket prices and calculate simulated PnL."""
import os
import json
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from poly_sports.data_fetching.fetch_realtime_prices import (
    extract_market_identifiers,
    parse_token_ids,
    fetch_market_prices_batch
)
from poly_sports.utils.file_utils import load_json, save_json
from poly_sports.processing.price_tracker import PriceTracker
from poly_sports.processing.pnl_calculator import PnLCalculator
from poly_sports.processing.arbitrage_calculation import detect_arbitrage_opportunities

try:
    from py_clob_client.client import ClobClient
except ImportError:
    print("Error: py-clob-client not installed. Install with: pip install py-clob-client")
    sys.exit(1)

# Load environment variables
load_dotenv()




def save_snapshots_to_csv(snapshots: List[Dict[str, Any]], filepath: str) -> None:
    """Save PnL snapshots to CSV file."""
    import csv
    
    if not snapshots:
        return
    
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    fieldnames = snapshots[0].keys()
    
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(snapshots)


def create_pnl_snapshot(
    market_id: str,
    event_id: str,
    outcome_name: str,
    entry_price: float,
    current_price: float,
    position_size: float,
    pnl_data: Dict[str, float],
    market_status: str
) -> Dict[str, Any]:
    """Create a PnL snapshot dictionary."""
    price_change = current_price - entry_price
    price_change_pct = (price_change / entry_price) if entry_price != 0 else 0.0
    
    return {
        "timestamp": datetime.now().isoformat(),
        "market_id": market_id,
        "event_id": event_id,
        "outcome_name": outcome_name,
        "entry_price": entry_price,
        "current_price": current_price,
        "price_change": price_change,
        "price_change_pct": price_change_pct,
        "position_size": position_size,
        "unrealized_pnl": pnl_data.get("unrealized_pnl", 0.0),
        "unrealized_pnl_pct": pnl_data.get("unrealized_pnl_pct", 0.0),
        "market_status": market_status
    }


def main() -> None:
    """Main monitoring function."""
    # Load configuration
    test_file = os.getenv("PNL_TEST_FILE", "data/arbitrage_comparison_test.json")
    poll_interval = int(os.getenv("PNL_POLL_INTERVAL", "30"))
    output_dir = os.getenv("PNL_OUTPUT_DIR", "data")
    clob_host = os.getenv("CLOB_HOST", "https://clob.polymarket.com")
    
    print(f"Loading events from {test_file}...")
    try:
        events = load_json(test_file)
        print(f"Loaded {len(events)} events")
    except FileNotFoundError:
        print(f"Error: Test file not found: {test_file}")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in test file: {e}")
        return
    
    # Filter active markets (not ended)
    active_events = [e for e in events if not e.get("pm_ended", False)]
    print(f"Found {len(active_events)} active markets")
    
    if not active_events:
        print("No active markets to monitor. Exiting.")
        return
    
    # Detect arbitrage opportunities to create positions
    print("Detecting arbitrage opportunities...")
    opportunities = detect_arbitrage_opportunities(active_events, min_profit_threshold=0.02)
    print(f"Found {len(opportunities)} opportunities")
    
    # Create positions from opportunities
    calculator = PnLCalculator()
    positions = {}
    market_to_event = {}
    
    for opp in opportunities:
        market_id = opp.get("pm_market_id")
        if not market_id:
            continue
        
        # Get entry price from first matched outcome
        matched_outcomes = opp.get("matched_outcomes", [])
        if not matched_outcomes:
            continue
        
        entry_price = matched_outcomes[0].get("pm_price")
        if entry_price is None:
            continue
        
        try:
            position = calculator.create_position(opp, entry_price)
            positions[market_id] = position
            market_to_event[market_id] = opp.get("pm_event_id")
        except Exception as e:
            print(f"Warning: Failed to create position for {market_id}: {e}")
            continue
    
    print(f"Created {len(positions)} positions")
    
    if not positions:
        print("No positions to monitor. Exiting.")
        return
    
    # Initialize tracker and CLOB client
    tracker = PriceTracker()
    clob_client = ClobClient(clob_host)
    
    # Prepare markets for batch fetching
    markets_to_fetch = []
    for event in active_events:
        market_id = event.get("pm_market_id")
        if market_id not in positions:
            continue
        
        identifiers = extract_market_identifiers(event)
        token_ids = identifiers.get("clob_token_ids", [])
        
        if token_ids:
            markets_to_fetch.append({
                "market_id": market_id,
                "token_ids": token_ids
            })
    
    print(f"Monitoring {len(markets_to_fetch)} markets")
    print(f"Polling interval: {poll_interval} seconds")
    print(f"Output directory: {output_dir}")
    print("\nStarting monitoring loop... (Press Ctrl+C to stop)\n")
    
    all_snapshots = []
    
    try:
        while True:
            timestamp = datetime.now()
            print(f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] Fetching prices...")
            
            # Fetch current prices
            try:
                current_prices_dict = fetch_market_prices_batch(clob_client, markets_to_fetch)
            except Exception as e:
                print(f"Error fetching prices: {e}")
                time.sleep(poll_interval)
                continue
            
            # Update tracker and calculate PnL
            snapshots = []
            
            for market_id, position in positions.items():
                # Check if market has ended
                event = next((e for e in active_events if e.get("pm_market_id") == market_id), None)
                if event and event.get("pm_ended", False):
                    tracker.mark_market_ended(market_id)
                    continue
                
                # Get current price for this market
                market_prices = current_prices_dict.get(market_id, {})
                if not market_prices:
                    continue
                
                # Use first available token price
                current_price = next(iter(market_prices.values()), None)
                if current_price is None:
                    continue
                
                # Update tracker
                tracker.add_snapshot(market_id, current_price, 0.01, timestamp)
                
                # Calculate PnL
                pnl_data = calculator.calculate_unrealized_pnl(position, current_price)
                
                # Create snapshot
                market_status = "ended" if tracker.is_market_ended(market_id) else "active"
                snapshot = create_pnl_snapshot(
                    market_id=market_id,
                    event_id=market_to_event.get(market_id, ""),
                    outcome_name=position.get("outcome_name", ""),
                    entry_price=position.get("entry_price", 0.0),
                    current_price=current_price,
                    position_size=position.get("position_size", 0.0),
                    pnl_data=pnl_data,
                    market_status=market_status
                )
                snapshots.append(snapshot)
                all_snapshots.append(snapshot)
                
                # Print summary
                pnl = pnl_data.get("unrealized_pnl", 0.0)
                pnl_pct = pnl_data.get("unrealized_pnl_pct", 0.0) * 100
                print(f"  {market_id}: ${pnl:.2f} ({pnl_pct:+.2f}%)")
            
            # Save snapshots periodically
            if snapshots:
                json_file = Path(output_dir) / "pnl_snapshots.json"
                csv_file = Path(output_dir) / "pnl_snapshots.csv"
                
                save_json(all_snapshots, str(json_file))
                save_snapshots_to_csv(all_snapshots, str(csv_file))
                
                print(f"  Saved {len(snapshots)} snapshots")
            
            # Check if all markets have ended
            active_count = sum(1 for m in markets_to_fetch if not tracker.is_market_ended(m["market_id"]))
            if active_count == 0:
                print("\nAll markets have ended. Stopping monitoring.")
                break
            
            # Wait for next poll
            time.sleep(poll_interval)
    
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user.")
        print(f"Total snapshots collected: {len(all_snapshots)}")
        
        # Save final snapshots
        if all_snapshots:
            json_file = Path(output_dir) / "pnl_snapshots.json"
            csv_file = Path(output_dir) / "pnl_snapshots.csv"
            
            save_json(all_snapshots, str(json_file))
            save_snapshots_to_csv(all_snapshots, str(csv_file))
            
            print(f"Final snapshots saved to {output_dir}/")


if __name__ == "__main__":
    main()

