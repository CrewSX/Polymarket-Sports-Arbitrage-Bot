"""Tests for price history tracking."""
import pytest
from datetime import datetime, timedelta
from poly_sports.processing.price_tracker import PriceTracker


class TestPriceTracker:
    """Test PriceTracker class."""
    
    def test_add_snapshot(self):
        """Test adding price snapshot with timestamp."""
        tracker = PriceTracker()
        timestamp = datetime.now()
        
        tracker.add_snapshot("664293", 0.595, 0.01, timestamp)
        
        history = tracker.get_history("664293")
        assert len(history) == 1
        assert history[0] == (timestamp, 0.595, 0.01)
    
    def test_add_multiple_snapshots(self):
        """Test adding multiple snapshots for same market."""
        tracker = PriceTracker()
        base_time = datetime.now()
        
        tracker.add_snapshot("664293", 0.595, 0.01, base_time)
        tracker.add_snapshot("664293", 0.60, 0.01, base_time + timedelta(seconds=30))
        tracker.add_snapshot("664293", 0.605, 0.01, base_time + timedelta(seconds=60))
        
        history = tracker.get_history("664293")
        assert len(history) == 3
        assert history[0][1] == 0.595
        assert history[2][1] == 0.605
    
    def test_get_history_empty(self):
        """Test retrieving history for market with no snapshots."""
        tracker = PriceTracker()
        
        history = tracker.get_history("664293")
        
        assert history == []
    
    def test_get_latest_price(self):
        """Test getting latest price for a market."""
        tracker = PriceTracker()
        base_time = datetime.now()
        
        tracker.add_snapshot("664293", 0.595, 0.01, base_time)
        tracker.add_snapshot("664293", 0.60, 0.01, base_time + timedelta(seconds=30))
        
        latest = tracker.get_latest_price("664293")
        
        assert latest == 0.60
    
    def test_get_latest_price_no_history(self):
        """Test getting latest price when no history exists."""
        tracker = PriceTracker()
        
        latest = tracker.get_latest_price("664293")
        
        assert latest is None
    
    def test_calculate_price_change(self):
        """Test calculating price change (absolute and percentage)."""
        tracker = PriceTracker()
        base_time = datetime.now()
        
        tracker.add_snapshot("664293", 0.595, 0.01, base_time)
        tracker.add_snapshot("664293", 0.60, 0.01, base_time + timedelta(seconds=30))
        
        change = tracker.calculate_price_change("664293")
        
        assert change["absolute"] == pytest.approx(0.005, rel=1e-6)
        assert change["percentage"] == pytest.approx(0.008403, rel=1e-3)  # 0.005 / 0.595
    
    def test_calculate_price_change_no_history(self):
        """Test calculating price change with no history."""
        tracker = PriceTracker()
        
        change = tracker.calculate_price_change("664293")
        
        assert change is None
    
    def test_calculate_price_change_single_snapshot(self):
        """Test calculating price change with only one snapshot."""
        tracker = PriceTracker()
        timestamp = datetime.now()
        
        tracker.add_snapshot("664293", 0.595, 0.01, timestamp)
        
        change = tracker.calculate_price_change("664293")
        
        assert change is None  # Need at least 2 snapshots
    
    def test_mark_market_ended(self):
        """Test marking market as ended."""
        tracker = PriceTracker()
        timestamp = datetime.now()
        
        tracker.add_snapshot("664293", 0.595, 0.01, timestamp)
        tracker.mark_market_ended("664293")
        
        assert tracker.is_market_ended("664293") is True
    
    def test_is_market_ended_false(self):
        """Test checking if market is ended when it's not."""
        tracker = PriceTracker()
        
        assert tracker.is_market_ended("664293") is False
    
    def test_filter_by_time_range(self):
        """Test filtering history by time range."""
        tracker = PriceTracker()
        base_time = datetime.now()
        
        tracker.add_snapshot("664293", 0.595, 0.01, base_time)
        tracker.add_snapshot("664293", 0.60, 0.01, base_time + timedelta(seconds=30))
        tracker.add_snapshot("664293", 0.605, 0.01, base_time + timedelta(seconds=60))
        tracker.add_snapshot("664293", 0.61, 0.01, base_time + timedelta(seconds=90))
        
        start_time = base_time + timedelta(seconds=15)
        end_time = base_time + timedelta(seconds=75)
        
        filtered = tracker.get_history("664293", start_time=start_time, end_time=end_time)
        
        assert len(filtered) == 2
        assert filtered[0][1] == 0.60
        assert filtered[1][1] == 0.605
    
    def test_multiple_markets(self):
        """Test tracking multiple markets independently."""
        tracker = PriceTracker()
        timestamp = datetime.now()
        
        tracker.add_snapshot("664293", 0.595, 0.01, timestamp)
        tracker.add_snapshot("664349", 0.56, 0.02, timestamp)
        
        assert tracker.get_latest_price("664293") == 0.595
        assert tracker.get_latest_price("664349") == 0.56
        
        history1 = tracker.get_history("664293")
        history2 = tracker.get_history("664349")
        
        assert len(history1) == 1
        assert len(history2) == 1

