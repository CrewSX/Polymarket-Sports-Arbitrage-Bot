"""Price history tracking for markets."""
from typing import List, Dict, Tuple, Optional
from datetime import datetime


class PriceTracker:
    """Track price history for multiple markets."""
    
    def __init__(self):
        """Initialize price tracker."""
        self._history: Dict[str, List[Tuple[datetime, float, float]]] = {}
        self._ended_markets: set = set()
    
    def add_snapshot(
        self,
        market_id: str,
        price: float,
        spread: float,
        timestamp: datetime
    ) -> None:
        """
        Add price snapshot for a market.
        
        Args:
            market_id: Market identifier
            price: Current price
            spread: Current spread
            timestamp: Timestamp of the snapshot
        """
        if market_id not in self._history:
            self._history[market_id] = []
        
        self._history[market_id].append((timestamp, price, spread))
        # Keep snapshots sorted by timestamp
        self._history[market_id].sort(key=lambda x: x[0])
    
    def get_history(
        self,
        market_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Tuple[datetime, float, float]]:
        """
        Get price history for a market.
        
        Args:
            market_id: Market identifier
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            List of (timestamp, price, spread) tuples, sorted by timestamp
        """
        if market_id not in self._history:
            return []
        
        history = self._history[market_id]
        
        if start_time is None and end_time is None:
            return history.copy()
        
        filtered = []
        for timestamp, price, spread in history:
            if start_time is not None and timestamp < start_time:
                continue
            if end_time is not None and timestamp > end_time:
                continue
            filtered.append((timestamp, price, spread))
        
        return filtered
    
    def get_latest_price(self, market_id: str) -> Optional[float]:
        """
        Get latest price for a market.
        
        Args:
            market_id: Market identifier
            
        Returns:
            Latest price, or None if no history exists
        """
        history = self.get_history(market_id)
        if not history:
            return None
        
        return history[-1][1]  # Return price from last snapshot
    
    def calculate_price_change(
        self,
        market_id: str
    ) -> Optional[Dict[str, float]]:
        """
        Calculate price change (absolute and percentage) for a market.
        
        Args:
            market_id: Market identifier
            
        Returns:
            Dictionary with 'absolute' and 'percentage' keys, or None if insufficient data
        """
        history = self.get_history(market_id)
        
        if len(history) < 2:
            return None
        
        first_price = history[0][1]
        latest_price = history[-1][1]
        
        absolute_change = latest_price - first_price
        percentage_change = (absolute_change / first_price) if first_price != 0 else 0.0
        
        return {
            "absolute": absolute_change,
            "percentage": percentage_change
        }
    
    def mark_market_ended(self, market_id: str) -> None:
        """
        Mark a market as ended.
        
        Args:
            market_id: Market identifier
        """
        self._ended_markets.add(market_id)
    
    def is_market_ended(self, market_id: str) -> bool:
        """
        Check if a market is marked as ended.
        
        Args:
            market_id: Market identifier
            
        Returns:
            True if market is ended, False otherwise
        """
        return market_id in self._ended_markets

