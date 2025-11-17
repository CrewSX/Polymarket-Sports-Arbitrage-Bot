"""Arbitrage calculation logic for detecting profitable opportunities."""
import json
from typing import List, Dict, Any, Optional


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
        return "2-way" if count >= 2 else "2-way"


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
    # Check if PM price is lower than SB implied probability
    if pm_price >= sb_implied_prob:
        return None
    
    # Calculate expected price movement
    expected_movement = sb_implied_prob - pm_price
    
    # Calculate potential profit percentage if price moves to fair value
    # Profit = (target_price - buy_price) / buy_price
    potential_profit = (sb_implied_prob - pm_price) / pm_price
    
    # Check if profit meets threshold
    if potential_profit < min_profit_threshold:
        return None
    
    return {
        "opportunity_type": "directional",
        "direction": "buy",
        "outcome_name": pm_outcome_name,
        "buy_price": pm_price,
        "target_price": sb_implied_prob,
        "expected_price_movement": expected_movement,
        "potential_profit_percentage": potential_profit,
        "potential_profit_absolute": potential_profit * 100.0  # For $100 stake
    }


def calculate_sell_points(
    buy_price: float,
    sb_implied_prob: float,
    target_profits: List[float] = [0.05, 0.10, 0.20]
) -> List[Dict[str, Any]]:
    """
    Calculate recommended sell points for directional opportunities.
    
    Since Polymarket prices are dynamic like stocks, recommend multiple exit points:
    - Fair value: When price reaches sportsbook implied probability (conservative)
    - Profit thresholds: At specified profit percentages (aggressive)
    
    Args:
        buy_price: Price at which to buy (decimal probability 0-1)
        sb_implied_prob: Sportsbook implied probability (target fair value)
        target_profits: List of profit percentages for sell points (default [5%, 10%, 20%])
        
    Returns:
        List of sell point dictionaries with target_price, profit_percentage, confidence, description
    """
    sell_points = []
    
    # Fair value sell point (conservative, high confidence)
    if sb_implied_prob > buy_price:
        fair_value_profit = (sb_implied_prob - buy_price) / buy_price
        sell_points.append({
            "target_price": sb_implied_prob,
            "profit_percentage": fair_value_profit,
            "confidence": "high",
            "description": "Fair value"
        })
    
    # Profit threshold sell points (aggressive, medium confidence)
    for profit_target in target_profits:
        target_price = buy_price * (1 + profit_target)
        
        # Only add if target price is reasonable (not above 1.0 for probabilities)
        if target_price <= 1.0:
            sell_points.append({
                "target_price": target_price,
                "profit_percentage": profit_target,
                "confidence": "medium",
                "description": f"{int(profit_target * 100)}% profit"
            })
    
    # Sort by target price (ascending)
    sell_points.sort(key=lambda x: x["target_price"])
    
    return sell_points


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
        
        # Try to find best match in SB outcomes
        best_match = None
        best_score = 0
        
        for sb_outcome in sb_outcomes:
            sb_name = sb_outcome.get('name', '')
            sb_name_lower = sb_name.lower()
            
            # Check if PM outcome name appears in SB outcome name or vice versa
            if pm_outcome_lower in sb_name_lower or sb_name_lower in pm_outcome_lower:
                # Calculate simple match score (length of common substring)
                common_length = min(len(pm_outcome_lower), len(sb_name_lower))
                if pm_outcome_lower in sb_name_lower:
                    score = len(pm_outcome_lower) / len(sb_name_lower)
                else:
                    score = len(sb_name_lower) / len(pm_outcome_lower)
                
                if score > best_score:
                    best_score = score
                    best_match = sb_outcome
        
        if best_match:
            matched[pm_outcome] = {
                'sb_outcome': best_match,
                'match_confidence': best_score  # Use score as confidence
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
                sb_price_decimal = sb_outcome.get('avg_price_decimal')
                
                if sb_implied_prob is None:
                    continue
                
                matched_outcomes_list.append({
                    'pm_outcome': pm_outcome,
                    'sb_outcome': sb_outcome.get('name', ''),
                    'pm_price': pm_price,
                    'sb_implied_prob': sb_implied_prob,
                    'sb_price_decimal': sb_price_decimal,
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
                    # Calculate sell points
                    sell_points = calculate_sell_points(pm_price, sb_implied_prob)
                    
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
                        'liquidity': entry.get('pm_event_liquidity'),
                        
                        # Matched outcomes
                        'matched_outcomes': [matched_outcome_data],
                        
                        # Sell points
                        'sell_points': sell_points,
                        
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

