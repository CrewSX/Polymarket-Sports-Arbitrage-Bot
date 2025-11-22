"""Arbitrage calculation logic for detecting profitable opportunities."""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from poly_sports.utils.odds_utils import american_to_implied_prob
from poly_sports.utils.file_utils import load_json


def detect_market_type(outcomes: List[str]) -> str:
    """
    Detect market type based on number of outcomes.
    
    Args:
        outcomes: List of outcome names
        
    Returns:
        '2-way' for 2 outcomes, '3-way' for 3 outcomes
    """
    count = len(outcomes)
    if count == 2:
        return "2-way"
    elif count == 3:
        return "3-way"
    else:
        # Handle edge cases - default to 2-way for now
        raise ValueError("Invalid market type")


def calculate_directional_opportunity(
    pm_price: float,
    sb_implied_prob: float,
    pm_outcome_name: str,
    min_profit_threshold: float = 0.1
) -> Optional[Dict[str, Any]]:
    """
    Calculate directional opportunity (buy when PM price < SB implied probability).
    
    This identifies when Polymarket undervalues an outcome compared to sportsbooks.
    If the outcome performs well, the PM price should rise toward the SB implied probability.
    
    Args:
        pm_price: Polymarket price (decimal probability 0-1)
        sb_implied_prob: Sportsbook implied probability (0-1)
        pm_outcome_name: Name of the Polymarket outcome
        min_profit_threshold: Minimum expected profit to consider (default 0.05 = 5%)
        
    Returns:
        Dictionary with directional opportunity details if exists, None otherwise
    """
    # Calculate expected price movement
    expected_movement = sb_implied_prob - pm_price
    
    # Calculate potential profit percentage if price moves to fair value
    # Profit = (target_price - buy_price) / buy_price
    potential_profit = (sb_implied_prob - pm_price) / pm_price
    delta_difference = abs(expected_movement)
    
    # Check if profit meets threshold
    if potential_profit < min_profit_threshold or delta_difference > 0.03:
        return None
    
    return {
        "opportunity_type": "directional",
        "direction": "buy",
        "outcome_name": pm_outcome_name,
        "buy_price": pm_price,
        "target_price": sb_implied_prob,
        "expected_price_movement": expected_movement,
        "potential_profit_percentage": potential_profit,
        "potential_profit_absolute": potential_profit * 100.0,  # For $100 stake
        "delta_difference": delta_difference
    }


def match_outcomes_by_name(
    pm_outcomes: List[str],
    sb_outcomes: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Match Polymarket outcomes to sportsbook outcomes by name.
    
    Since the data is already matched at the event level, we just need to match
    individual outcomes by checking if PM outcome names appear in SB outcome names.
    
    Args:
        pm_outcomes: List of Polymarket outcome names (e.g., ["Texas State", "Louisiana"])
        sb_outcomes: List of sportsbook outcome dictionaries with 'name' field
        
    Returns:
        Dictionary mapping PM outcome names to matched SB outcome data
    """
    matched = {}
    
    for pm_outcome in pm_outcomes:
        pm_outcome_lower = pm_outcome.lower()
        for sb_outcome in sb_outcomes:
            sb_name = sb_outcome.get('name', '')
            sb_name_lower = sb_name.lower()
            # Check if PM outcome name appears in SB outcome name or vice versa
            if pm_outcome_lower in sb_name_lower or sb_name_lower in pm_outcome_lower:
                matched[pm_outcome] = {
                    'sb_outcome': sb_outcome
                }
        
    return matched


def detect_arbitrage_opportunities(
    comparison_data: List[Dict[str, Any]],
    min_profit_threshold: float = 0.02,
    min_liquidity: float = 1000,
    pm_fee: float = 0.0,
    sb_fee: float = 0.0
) -> List[Dict[str, Any]]:
    """
    Main function to detect arbitrage opportunities from comparison data.
    
    Processes matched Polymarket and sportsbook data to identify directional opportunities
    (price movement trading). Note: Traditional arbitrage is not applicable since Polymarket
    prices always sum to 1.0.
    
    Args:
        comparison_data: List of comparison dictionaries from arbitrage_comparison_test.json
        min_profit_threshold: Minimum profit margin to consider (default 0.02 = 2%)
        pm_fee: Polymarket transaction fee (default 0.0, reserved for future use)
        sb_fee: Sportsbook fee (default 0.0, reserved for future use)
        
    Returns:
        List of opportunity dictionaries with full details
    """
    opportunities = []
    
    for entry in comparison_data:
        try:
            # Extract required fields
            pm_outcomes_str = entry.get('pm_market_outcomes', '')
            pm_prices_str = entry.get('pm_market_outcomePrices', '')
            sb_outcomes = entry.get('sportsbook_outcomes', [])
            
            # Skip if missing required data
            if not pm_outcomes_str or not pm_prices_str or not sb_outcomes:
                continue
            
            # Parse JSON strings
            try:
                pm_outcomes = json.loads(pm_outcomes_str) if isinstance(pm_outcomes_str, str) else pm_outcomes_str
                pm_prices = [float(p) for p in json.loads(pm_prices_str)] if isinstance(pm_prices_str, str) else pm_prices_str
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
            
            # Match outcomes by name (data is already matched at event level)
            matched_outcomes = match_outcomes_by_name(pm_outcomes, sb_outcomes)
            
            if not matched_outcomes:
                continue
            
            # Extract matched prices and probabilities
            matched_outcomes_list = []
            
            for pm_outcome, match_data in matched_outcomes.items():
                pm_price = None
                # Find PM price for this outcome
                for i, outcome_name in enumerate(pm_outcomes):
                    if outcome_name == pm_outcome and i < len(pm_prices):
                        pm_price = pm_prices[i]
                        break
                
                if pm_price is None:
                    continue
                
                sb_outcome = match_data['sb_outcome']
                sb_implied_prob = sb_outcome.get('avg_implied_probability')
                
                if sb_implied_prob is None:
                    continue
                
                matched_outcomes_list.append({
                    'pm_outcome': pm_outcome,
                    'sb_outcome': sb_outcome.get('name', ''),
                    'pm_price': pm_price,
                    'sb_implied_prob': sb_implied_prob,
                    'match_confidence': match_data['match_confidence']
                })
            
            if not matched_outcomes_list:
                continue
            
            # Detect market type
            market_type = detect_market_type(pm_outcomes)
            
            # Check for directional opportunities using the matched outcomes list
            for matched_outcome_data in matched_outcomes_list:
                pm_price = matched_outcome_data['pm_price']
                sb_implied_prob = matched_outcome_data['sb_implied_prob']
                pm_outcome = matched_outcome_data['pm_outcome']
                
                directional_result = calculate_directional_opportunity(
                    pm_price,
                    sb_implied_prob,
                    pm_outcome,
                    min_profit_threshold=min_profit_threshold
                )
                
                if directional_result:
                    
                    opportunity = {
                        # Original data
                        'pm_event_id': entry.get('pm_event_id'),
                        'pm_market_id': entry.get('pm_market_id'),
                        'odds_api_event_id': entry.get('odds_api_event_id'),
                        'match_confidence': entry.get('match_confidence'),
                        
                        # Opportunity details
                        'opportunity_type': 'directional',
                        'market_type': market_type,
                        'profit_margin': directional_result['potential_profit_percentage'],
                        'profit_margin_absolute': directional_result['potential_profit_absolute'],
                        'delta_difference': directional_result['delta_difference'],
                        'liquidity': entry.get('pm_event_liquidity'),
                        'volume': entry.get('pm_market_volume'),
                        
                        # Matched outcomes
                        'matched_outcomes': [matched_outcome_data],
                        
                        # Additional context
                        'pm_spread': entry.get('pm_spread'),
                        'pm_liquidity': entry.get('pm_market_liquidityNum'),
                        'sportsbook_count': entry.get('sportsbook_count', 0)
                    }
                    
                    opportunities.append(opportunity)
        
        except Exception:
            # Skip entries that cause errors
            continue
    
    # Filter by profit threshold (double-check)
    opportunities = [opp for opp in opportunities if opp.get('profit_margin', 0) >= min_profit_threshold and opp.get('liquidity', 0) >= min_liquidity]
    
    return opportunities


def find_max_delta_by_sportsbook(
    comparison_data: List[Dict[str, Any]],
    odds_dir: str = 'data/sportsbook_data/odds/',
    top_n: int = 50
) -> List[Dict[str, Any]]:
    """
    Find the sportsbook with the largest delta_difference for each event.
    
    For each event, compares Polymarket prices with individual sportsbook odds
    to find the sportsbook with the maximum delta_difference (difference between
    sportsbook implied probability and Polymarket price).
    
    Args:
        comparison_data: List of comparison dictionaries from arbitrage_comparison.json
            Each entry should have:
            - odds_api_event_id: Event ID to match with raw odds data
            - pm_market_outcomes: JSON string or list of Polymarket outcome names
            - pm_market_outcomePrices: JSON string or list of Polymarket prices
        odds_dir: Directory path to raw odds JSON files (default: 'data/sportsbook_data/odds/')
        top_n: Number of top events to return, sorted by highest delta_difference (default: 50)
        
    Returns:
        List of top N event dictionaries, each containing:
        - All original fields from comparison_data
        - max_delta: Dictionary with:
            - sportsbook_name: Sportsbook key (e.g., 'fanduel')
            - sportsbook_title: Sportsbook display name (e.g., 'FanDuel')
            - delta_difference: Maximum delta_difference found
            - outcome_name: Name of the outcome with max delta
            - pm_price: Polymarket price for that outcome
            - sb_implied_prob: Sportsbook implied probability for that outcome
    """
    # Step 1: Load all raw odds JSON files and create event mapping
    odds_path = Path(odds_dir)
    if not odds_path.exists():
        raise FileNotFoundError(f"Odds directory not found: {odds_dir}")
    
    # Create mapping of event_id -> event data with bookmakers
    odds_by_event_id = {}
    
    for odds_file in odds_path.glob('*.json'):
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
    
    # Step 2: Process each event in comparison_data
    events_with_deltas = []
    
    for entry in comparison_data:
        try:
            odds_api_event_id = entry.get('odds_api_event_id')
            if not odds_api_event_id:
                continue
            
            # Find matching raw odds event
            raw_odds_event = odds_by_event_id.get(odds_api_event_id)
            if not raw_odds_event or not raw_odds_event.get('bookmakers'):
                continue
            
            # Extract Polymarket outcomes and prices
            pm_outcomes_str = entry.get('pm_market_outcomes', '')
            pm_prices_str = entry.get('pm_market_outcomePrices', '')
            
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
            
            # Step 4: Match Polymarket outcomes to sportsbook outcomes using existing matching function
            # This ensures we're matching the correct outcomes within the same event
            matched_outcomes = match_outcomes_by_name(pm_outcomes, raw_odds_event.get('bookmakers', []).get('markets', []).get('outcomes', []).get('name', ''))
            
            if not matched_outcomes:
                continue
            
            # Step 5: For each matched outcome, find max delta_difference across all sportsbooks
            max_delta_info = None
            max_delta_value = float('-inf')
            
            for pm_outcome_name, match_data in matched_outcomes.items():
                # Get the matched sportsbook outcome name
                matched_sb_outcome_name = match_data['sb_outcome'].get('name', '')
                if not matched_sb_outcome_name:
                    continue
                
                # Find PM price for this outcome
                pm_price = None
                for i, outcome_name in enumerate(pm_outcomes):
                    if outcome_name == pm_outcome_name and i < len(pm_prices):
                        pm_price = pm_prices[i]
                        break
                
                if pm_price is None:
                    continue
                
                # Now check each sportsbook for this specific matched outcome
                # We use the matched sportsbook outcome name to find the same outcome in each bookmaker
                matched_sb_outcome_lower = matched_sb_outcome_name.lower()
                
                for bookmaker in raw_odds_event.get('bookmakers', []):
                    bookmaker_key = bookmaker.get('key', '')
                    bookmaker_title = bookmaker.get('title', '')
                    
                    # Look through markets for the matched outcome
                    for market in bookmaker.get('markets', []):
                        for outcome in market.get('outcomes', []):
                            sb_outcome_name = outcome.get('name', '')
                            sb_outcome_lower = sb_outcome_name.lower()
                            
                            # Match outcomes: prefer exact match to ensure we're comparing the same team/outcome
                            # This prevents matching across different teams (e.g., "Texas" vs "Texas State")
                            # Allow substring matching as fallback, but only for longer names to avoid false matches
                            is_exact_match = (sb_outcome_lower == matched_sb_outcome_lower)
                            is_substring_match = (
                                (matched_sb_outcome_lower in sb_outcome_lower or 
                                 sb_outcome_lower in matched_sb_outcome_lower) and
                                len(matched_sb_outcome_lower) > 5  # Avoid matching short names incorrectly
                            )
                            
                            # Only consider outcomes that match the matched outcome name
                            # This ensures we're comparing the same team/outcome across sportsbooks
                            if is_exact_match or is_substring_match:
                                # Get American odds price
                                american_price = outcome.get('price')
                                if american_price is None:
                                    continue
                                
                                # Convert to implied probability
                                try:
                                    sb_implied_prob = american_to_implied_prob(int(american_price))
                                except (ValueError, TypeError):
                                    continue
                                
                                # Calculate delta_difference
                                delta_difference = abs(sb_implied_prob - pm_price)
                                
                                # Track maximum delta_difference
                                if delta_difference > max_delta_value:
                                    max_delta_value = delta_difference
                                    max_delta_info = {
                                        'sportsbook_name': bookmaker_key,
                                        'sportsbook_title': bookmaker_title,
                                        'delta_difference': delta_difference,
                                        'outcome_name': pm_outcome_name,
                                        'pm_price': pm_price,
                                        'sb_implied_prob': sb_implied_prob,
                                        'sb_outcome_name': matched_sb_outcome_name,
                                        'match_confidence': match_data.get('match_confidence', 0)
                                    }
            
            # Step 4: If we found a max delta, add event with delta info
            if max_delta_info and max_delta_value > float('-inf'):
                result_entry = entry.copy()
                result_entry['max_delta'] = max_delta_info
                events_with_deltas.append(result_entry)
        
        except Exception:
            # Skip entries that cause errors
            continue
    
    # Step 5: Sort by delta_difference (descending) and return top N
    events_with_deltas.sort(
        key=lambda x: x.get('max_delta', {}).get('delta_difference', float('-inf')),
        reverse=True
    )
    
    return events_with_deltas[:top_n]

