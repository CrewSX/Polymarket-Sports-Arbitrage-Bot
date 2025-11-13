"""Tests for PnL calculation."""
import pytest
from poly_sports.processing.pnl_calculator import PnLCalculator


class TestPnLCalculator:
    """Test PnLCalculator class."""
    
    def test_create_position_from_opportunity(self):
        """Test creating position from arbitrage opportunity."""
        calculator = PnLCalculator()
        
        opportunity = {
            "pm_market_id": "664293",
            "pm_event_id": "72621",
            "opportunity_type": "directional",
            "matched_outcomes": [{
                "pm_outcome": "Texas State",
                "pm_price": 0.595,
                "sb_implied_prob": 0.7,
                "sb_price_decimal": 1.43
            }],
            "profit_margin": 0.176,  # 17.6%
            "profit_margin_absolute": 17.6
        }
        
        position = calculator.create_position(opportunity, entry_price=0.595)
        
        assert position["market_id"] == "664293"
        assert position["event_id"] == "72621"
        assert position["entry_price"] == 0.595
        assert position["outcome_name"] == "Texas State"
        assert position["position_size"] == pytest.approx(17.6, rel=1e-3)  # Based on profit_margin_absolute
        assert "created_at" in position
    
    def test_calculate_unrealized_pnl_positive(self):
        """Test calculating unrealized PnL with positive change."""
        calculator = PnLCalculator()
        
        position = {
            "entry_price": 0.595,
            "position_size": 100.0,
            "outcome_name": "Texas State"
        }
        
        current_price = 0.65
        
        pnl = calculator.calculate_unrealized_pnl(position, current_price)
        
        # PnL = (0.65 - 0.595) / 0.595 * 100 = 0.0924 * 100 = 9.24
        expected_pnl = (0.65 - 0.595) / 0.595 * 100
        assert pnl["unrealized_pnl"] == pytest.approx(expected_pnl, rel=1e-3)
        assert pnl["unrealized_pnl_pct"] == pytest.approx(0.0924, rel=1e-3)
        assert pnl["current_price"] == 0.65
    
    def test_calculate_unrealized_pnl_negative(self):
        """Test calculating unrealized PnL with negative change."""
        calculator = PnLCalculator()
        
        position = {
            "entry_price": 0.595,
            "position_size": 100.0,
            "outcome_name": "Texas State"
        }
        
        current_price = 0.55
        
        pnl = calculator.calculate_unrealized_pnl(position, current_price)
        
        expected_pnl = (0.55 - 0.595) / 0.595 * 100
        assert pnl["unrealized_pnl"] == pytest.approx(expected_pnl, rel=1e-3)
        assert pnl["unrealized_pnl_pct"] < 0
    
    def test_calculate_unrealized_pnl_zero_change(self):
        """Test calculating unrealized PnL with zero price change."""
        calculator = PnLCalculator()
        
        position = {
            "entry_price": 0.595,
            "position_size": 100.0,
            "outcome_name": "Texas State"
        }
        
        current_price = 0.595
        
        pnl = calculator.calculate_unrealized_pnl(position, current_price)
        
        assert pnl["unrealized_pnl"] == pytest.approx(0.0, abs=1e-6)
        assert pnl["unrealized_pnl_pct"] == pytest.approx(0.0, abs=1e-6)
    
    def test_calculate_realized_pnl(self):
        """Test calculating realized PnL when position is closed."""
        calculator = PnLCalculator()
        
        position = {
            "entry_price": 0.595,
            "position_size": 100.0,
            "outcome_name": "Texas State"
        }
        
        exit_price = 0.65
        
        pnl = calculator.calculate_realized_pnl(position, exit_price)
        
        expected_pnl = (0.65 - 0.595) / 0.595 * 100
        assert pnl["realized_pnl"] == pytest.approx(expected_pnl, rel=1e-3)
        assert pnl["realized_pnl_pct"] == pytest.approx(0.0924, rel=1e-3)
        assert pnl["exit_price"] == 0.65
    
    def test_get_total_pnl_single_position(self):
        """Test calculating total PnL with single position."""
        calculator = PnLCalculator()
        
        positions = {
            "664293": {
                "entry_price": 0.595,
                "position_size": 100.0,
                "outcome_name": "Texas State"
            }
        }
        
        current_prices = {"664293": 0.65}
        
        total = calculator.get_total_pnl(positions, current_prices)
        
        expected_pnl = (0.65 - 0.595) / 0.595 * 100
        assert total["total_unrealized_pnl"] == pytest.approx(expected_pnl, rel=1e-3)
        assert total["position_count"] == 1
    
    def test_get_total_pnl_multiple_positions(self):
        """Test calculating total PnL with multiple positions."""
        calculator = PnLCalculator()
        
        positions = {
            "664293": {
                "entry_price": 0.595,
                "position_size": 100.0,
                "outcome_name": "Texas State"
            },
            "664349": {
                "entry_price": 0.56,
                "position_size": 150.0,
                "outcome_name": "Louisiana"
            }
        }
        
        current_prices = {
            "664293": 0.65,
            "664349": 0.50
        }
        
        total = calculator.get_total_pnl(positions, current_prices)
        
        pnl1 = (0.65 - 0.595) / 0.595 * 100
        pnl2 = (0.50 - 0.56) / 0.56 * 150
        expected_total = pnl1 + pnl2
        
        assert total["total_unrealized_pnl"] == pytest.approx(expected_total, rel=1e-3)
        assert total["position_count"] == 2
    
    def test_get_total_pnl_missing_price(self):
        """Test calculating total PnL when some prices are missing."""
        calculator = PnLCalculator()
        
        positions = {
            "664293": {
                "entry_price": 0.595,
                "position_size": 100.0,
                "outcome_name": "Texas State"
            },
            "664349": {
                "entry_price": 0.56,
                "position_size": 150.0,
                "outcome_name": "Louisiana"
            }
        }
        
        current_prices = {
            "664293": 0.65
            # Missing 664349
        }
        
        total = calculator.get_total_pnl(positions, current_prices)
        
        # Should only calculate for available prices
        pnl1 = (0.65 - 0.595) / 0.595 * 100
        assert total["total_unrealized_pnl"] == pytest.approx(pnl1, rel=1e-3)
        assert total["position_count"] == 1  # Only one with price
    
    def test_position_sizing_from_opportunity(self):
        """Test position sizing based on opportunity size."""
        calculator = PnLCalculator()
        
        # Opportunity with profit_margin_absolute indicating position size
        opportunity = {
            "pm_market_id": "664293",
            "pm_event_id": "72621",
            "opportunity_type": "directional",
            "matched_outcomes": [{
                "pm_outcome": "Texas State",
                "pm_price": 0.595,
                "sb_implied_prob": 0.7
            }],
            "profit_margin": 0.176,
            "profit_margin_absolute": 50.0  # $50 position size
        }
        
        position = calculator.create_position(opportunity, entry_price=0.595)
        
        # Position size should be based on profit_margin_absolute
        assert position["position_size"] == pytest.approx(50.0, rel=1e-3)
    
    def test_multiple_outcomes_per_market(self):
        """Test handling multiple outcomes per market."""
        calculator = PnLCalculator()
        
        opportunity = {
            "pm_market_id": "664293",
            "pm_event_id": "72621",
            "opportunity_type": "directional",
            "matched_outcomes": [
                {
                    "pm_outcome": "Texas State",
                    "pm_price": 0.595,
                    "sb_implied_prob": 0.7
                },
                {
                    "pm_outcome": "Louisiana",
                    "pm_price": 0.405,
                    "sb_implied_prob": 0.3
                }
            ],
            "profit_margin": 0.176,
            "profit_margin_absolute": 17.6
        }
        
        # Should create position for first matched outcome
        position = calculator.create_position(opportunity, entry_price=0.595)
        
        assert position["outcome_name"] == "Texas State"
        assert position["entry_price"] == 0.595

