"""Fetch real-time prices from Polymarket CLOB API for markets in test data."""
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from poly_sports.utils.file_utils import load_json


def extract_market_identifiers(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract market identifiers from event dictionary.
    
    Args:
        event: Event dictionary with pm_* fields
        
    Returns:
        Dictionary with market_id, condition_id, event_id, and clob_token_ids
    """
    identifiers = {
        "market_id": event.get("pm_market_id"),
        "condition_id": event.get("pm_conditionId"),
        "event_id": event.get("pm_event_id"),
        "clob_token_ids": parse_token_ids(event.get("pm_clobTokenIds")),
    }
    
    return identifiers


def parse_token_ids(clob_token_ids: Optional[str]) -> List[str]:
    """
    Parse token IDs from JSON string format.
    
    Args:
        clob_token_ids: JSON string of token IDs or list, or None
        
    Returns:
        List of token ID strings
        
    Raises:
        json.JSONDecodeError: If string is invalid JSON
    """
    if clob_token_ids is None:
        return []
    
    if isinstance(clob_token_ids, list):
        return clob_token_ids
    
    if not clob_token_ids or clob_token_ids.strip() == "":
        return []
    
    try:
        parsed = json.loads(clob_token_ids)
        if isinstance(parsed, list):
            return [str(token_id) for token_id in parsed]
        return []
    except json.JSONDecodeError:
        raise


def fetch_market_price(clob_client: Any, token_id: str) -> Optional[float]:
    """
    Fetch current price for a market token using CLOB API.
    
    Tries midpoint first, falls back to buy price if midpoint unavailable.
    
    Args:
        clob_client: Initialized CLOB client instance
        token_id: Token ID to fetch price for
        
    Returns:
        Current price as float, or None if unavailable
    """
    try:
        # Try midpoint first
        midpoint_response = clob_client.get_midpoint(token_id)
        if midpoint_response and midpoint_response.get("mid"):
            try:
                return float(midpoint_response["mid"])
            except (ValueError, TypeError):
                pass
        
        # Fallback to buy price
        buy_price_response = clob_client.get_price(token_id, side="BUY")
        if buy_price_response and buy_price_response.get("price"):
            try:
                return float(buy_price_response["price"])
            except (ValueError, TypeError):
                pass
        
        return None
    except Exception:
        return None


def fetch_market_prices_batch(
    clob_client: Any,
    markets: List[Dict[str, Any]]
) -> Dict[str, Dict[str, float]]:
    """
    Fetch prices for multiple markets in batch.
    
    Args:
        clob_client: Initialized CLOB client instance
        markets: List of market dictionaries, each with:
            - market_id: Market identifier
            - token_ids: List of token IDs for this market
            
    Returns:
        Dictionary mapping market_id to dictionary of token_id -> price
        Example: {"664293": {"token1": 0.595, "token2": 0.405}}
    """
    results = {}
    
    for market in markets:
        market_id = market.get("market_id")
        token_ids = market.get("token_ids", [])
        
        if not market_id:
            continue
        
        market_prices = {}
        
        for token_id in token_ids:
            price = fetch_market_price(clob_client, token_id)
            if price is not None:
                market_prices[token_id] = price
        
        results[market_id] = market_prices
    
    return results

