"""PnL calculation for simulated positions."""
from typing import Dict, Any, List, Optional
from datetime import datetime


class PnLCalculator:
    """Calculate Profit and Loss for simulated trading positions."""
    
    def create_position(
        self,
        opportunity: Dict[str, Any],
        entry_price: float
    ) -> Dict[str, Any]:
        """
        Create a position from an arbitrage opportunity.
        
        Args:
            opportunity: Opportunity dictionary from detect_arbitrage_opportunities
            entry_price: Entry price for the position
            
        Returns:
            Position dictionary with entry_price, position_size, etc.
        """
        # Get first matched outcome (primary opportunity)
        matched_outcomes = opportunity.get("matched_outcomes", [])
        if not matched_outcomes:
            raise ValueError("Opportunity must have at least one matched outcome")
        
        primary_outcome = matched_outcomes[0]
        
        # Position size based on profit_margin_absolute from opportunity
        # This represents the potential profit for a $100 stake
        # We use it as the position size
        position_size = opportunity.get("profit_margin_absolute", 100.0)
        
        position = {
            "market_id": opportunity.get("pm_market_id"),
            "event_id": opportunity.get("pm_event_id"),
            "outcome_name": primary_outcome.get("pm_outcome"),
            "entry_price": entry_price,
            "position_size": position_size,
            "opportunity_type": opportunity.get("opportunity_type", "directional"),
            "created_at": datetime.now().isoformat()
        }
        
        return position
    
    def calculate_unrealized_pnl(
        self,
        position: Dict[str, Any],
        current_price: float
    ) -> Dict[str, float]:
        """
        Calculate unrealized PnL for a position.
        
        Args:
            position: Position dictionary
            current_price: Current market price
            
        Returns:
            Dictionary with unrealized_pnl, unrealized_pnl_pct, current_price
        """
        entry_price = position["entry_price"]
        position_size = position["position_size"]
        
        if entry_price == 0:
            return {
                "unrealized_pnl": 0.0,
                "unrealized_pnl_pct": 0.0,
                "current_price": current_price
            }
        
        # PnL percentage = (current_price - entry_price) / entry_price
        pnl_percentage = (current_price - entry_price) / entry_price
        
        # Unrealized PnL = pnl_percentage * position_size
        unrealized_pnl = pnl_percentage * position_size
        
        return {
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": pnl_percentage,
            "current_price": current_price
        }
    
    def calculate_realized_pnl(
        self,
        position: Dict[str, Any],
        exit_price: float
    ) -> Dict[str, float]:
        """
        Calculate realized PnL when position is closed.
        
        Args:
            position: Position dictionary
            exit_price: Price at which position was closed
            
        Returns:
            Dictionary with realized_pnl, realized_pnl_pct, exit_price
        """
        entry_price = position["entry_price"]
        position_size = position["position_size"]
        
        if entry_price == 0:
            return {
                "realized_pnl": 0.0,
                "realized_pnl_pct": 0.0,
                "exit_price": exit_price
            }
        
        # PnL percentage = (exit_price - entry_price) / entry_price
        pnl_percentage = (exit_price - entry_price) / entry_price
        
        # Realized PnL = pnl_percentage * position_size
        realized_pnl = pnl_percentage * position_size
        
        return {
            "realized_pnl": realized_pnl,
            "realized_pnl_pct": pnl_percentage,
            "exit_price": exit_price
        }
    
    def get_total_pnl(
        self,
        positions: Dict[str, Dict[str, Any]],
        current_prices: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Calculate total PnL across all positions.
        
        Args:
            positions: Dictionary mapping market_id to position
            current_prices: Dictionary mapping market_id to current price
            
        Returns:
            Dictionary with total_unrealized_pnl, position_count, etc.
        """
        total_pnl = 0.0
        position_count = 0
        
        for market_id, position in positions.items():
            if market_id not in current_prices:
                continue
            
            current_price = current_prices[market_id]
            pnl_data = self.calculate_unrealized_pnl(position, current_price)
            total_pnl += pnl_data["unrealized_pnl"]
            position_count += 1
        
        return {
            "total_unrealized_pnl": total_pnl,
            "position_count": position_count,
            "average_pnl_per_position": total_pnl / position_count if position_count > 0 else 0.0
        }

