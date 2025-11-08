"""Odds format conversion utilities for sports betting odds."""
from typing import Union


def american_to_decimal(american_odds: int) -> float:
    """
    Convert American odds to decimal odds.
    
    Formula:
    - Positive American odds: decimal = (american / 100) + 1
    - Negative American odds: decimal = (100 / abs(american)) + 1
    
    Args:
        american_odds: American odds (e.g., 100, -150, 200)
        
    Returns:
        Decimal odds (e.g., 2.0, 1.666..., 3.0)
    """
    if american_odds > 0:
        return (american_odds / 100.0) + 1.0
    else:
        return (100.0 / abs(american_odds)) + 1.0


def decimal_to_american(decimal_odds: float) -> int:
    """
    Convert decimal odds to American odds.
    
    Formula:
    - If decimal >= 2.0: american = (decimal - 1) * 100
    - If decimal < 2.0: american = -100 / (decimal - 1)
    
    Args:
        decimal_odds: Decimal odds (e.g., 2.0, 1.5, 3.0)
        
    Returns:
        American odds (e.g., 100, -200, 200)
    """
    if decimal_odds >= 2.0:
        return int(round((decimal_odds - 1.0) * 100))
    else:
        return int(round(-100.0 / (decimal_odds - 1.0)))


def american_to_implied_prob(american_odds: int) -> float:
    """
    Convert American odds to implied probability (0-1).
    
    Formula:
    - Positive American odds: prob = 100 / (american + 100)
    - Negative American odds: prob = abs(american) / (abs(american) + 100)
    
    Args:
        american_odds: American odds (e.g., 100, -150, 200)
        
    Returns:
        Implied probability between 0 and 1
    """
    if american_odds > 0:
        return 100.0 / (american_odds + 100.0)
    else:
        return abs(american_odds) / (abs(american_odds) + 100.0)


def decimal_to_implied_prob(decimal_odds: float) -> float:
    """
    Convert decimal odds to implied probability (0-1).
    
    Formula: prob = 1 / decimal
    
    Args:
        decimal_odds: Decimal odds (e.g., 2.0, 1.5, 3.0)
        
    Returns:
        Implied probability between 0 and 1
    """
    return 1.0 / decimal_odds


def implied_prob_to_american(prob: float) -> int:
    """
    Convert implied probability (0-1) to American odds.
    
    Formula:
    - If prob < 0.5: american = (100 / prob) - 100
    - If prob == 0.5: american = 100 (even money)
    - If prob > 0.5: american = -100 * prob / (1 - prob)
    
    Args:
        prob: Implied probability between 0 and 1
        
    Returns:
        American odds (e.g., 100, -150, 200)
    """
    if abs(prob - 0.5) < 1e-10:  # Handle even money case
        return 100
    elif prob < 0.5:
        return int(round((100.0 / prob) - 100.0))
    else:
        return int(round(-100.0 * prob / (1.0 - prob)))


def implied_prob_to_decimal(prob: float) -> float:
    """
    Convert implied probability (0-1) to decimal odds.
    
    Formula: decimal = 1 / prob
    
    Args:
        prob: Implied probability between 0 and 1
        
    Returns:
        Decimal odds (e.g., 2.0, 1.5, 3.0)
    """
    return 1.0 / prob

