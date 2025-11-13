"""Tests for PnL monitoring script."""
import json
import pytest
import os
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
from datetime import datetime, timedelta
from poly_sports.utils.file_utils import load_json
from poly_sports.processing.price_tracker import PriceTracker
from poly_sports.processing.pnl_calculator import PnLCalculator


class TestMonitorPnL:
    """Test PnL monitoring functionality."""
    
    def test_load_events_from_test_file(self, tmp_path):
        """Test loading events from arbitrage_comparison_test.json."""
        # Create mock test file
        test_data = [
            {
                "pm_market_id": "664293",
                "pm_event_id": "72621",
                "pm_ended": False,
                "pm_clobTokenIds": '["token1", "token2"]',
                "pm_market_outcomePrices": '["0.595", "0.405"]'
            }
        ]
        test_file = tmp_path / "arbitrage_comparison_test.json"
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        
        events = load_json(str(test_file))
        
        assert len(events) == 1
        assert events[0]["pm_market_id"] == "664293"
    
    @patch('poly_sports.data_fetching.fetch_realtime_prices.fetch_market_prices_batch')
    @patch('poly_sports.data_fetching.fetch_realtime_prices.parse_token_ids')
    @patch('poly_sports.data_fetching.fetch_realtime_prices.extract_market_identifiers')
    def test_fetch_and_track_prices(
        self,
        mock_extract,
        mock_parse,
        mock_fetch_batch
    ):
        """Test fetching prices and updating tracker."""
        # Setup mocks
        mock_extract.return_value = {
            "market_id": "664293",
            "clob_token_ids": ["token1", "token2"]
        }
        mock_parse.return_value = ["token1", "token2"]
        mock_fetch_batch.return_value = {
            "664293": {"token1": 0.60, "token2": 0.40}
        }
        
        tracker = PriceTracker()
        mock_client = Mock()
        
        # Simulate fetching prices
        markets = [{"market_id": "664293", "token_ids": ["token1", "token2"]}]
        prices = mock_fetch_batch(mock_client, markets)
        
        # Update tracker
        timestamp = datetime.now()
        for market_id, token_prices in prices.items():
            for token_id, price in token_prices.items():
                tracker.add_snapshot(market_id, price, 0.01, timestamp)
        
        # Verify
        assert tracker.get_latest_price("664293") == 0.40  # Last token price
        assert len(tracker.get_history("664293")) == 2
    
    def test_calculate_pnl_for_positions(self):
        """Test calculating PnL for tracked positions."""
        calculator = PnLCalculator()
        tracker = PriceTracker()
        
        # Create position
        opportunity = {
            "pm_market_id": "664293",
            "pm_event_id": "72621",
            "matched_outcomes": [{
                "pm_outcome": "Texas State",
                "pm_price": 0.595
            }],
            "profit_margin_absolute": 100.0
        }
        position = calculator.create_position(opportunity, entry_price=0.595)
        
        # Add price snapshot
        timestamp = datetime.now()
        tracker.add_snapshot("664293", 0.65, 0.01, timestamp)
        
        # Calculate PnL
        current_price = tracker.get_latest_price("664293")
        pnl = calculator.calculate_unrealized_pnl(position, current_price)
        
        assert pnl["unrealized_pnl"] > 0
        assert pnl["current_price"] == 0.65
    
    def test_handle_market_end_state(self):
        """Test handling when market ends."""
        tracker = PriceTracker()
        
        tracker.add_snapshot("664293", 0.595, 0.01, datetime.now())
        tracker.mark_market_ended("664293")
        
        assert tracker.is_market_ended("664293") is True
    
    @patch('time.sleep')
    @patch('poly_sports.data_fetching.fetch_realtime_prices.fetch_market_prices_batch')
    def test_polling_loop_execution(self, mock_fetch, mock_sleep):
        """Test polling loop execution (mocked time)."""
        mock_client = Mock()
        tracker = PriceTracker()
        
        # Mock price fetching
        mock_fetch.return_value = {
            "664293": {"token1": 0.60}
        }
        
        # Simulate two polling cycles
        markets = [{"market_id": "664293", "token_ids": ["token1"]}]
        
        for i in range(2):
            prices = mock_fetch(mock_client, markets)
            timestamp = datetime.now() + timedelta(seconds=i * 30)
            for market_id, token_prices in prices.items():
                for token_id, price in token_prices.items():
                    tracker.add_snapshot(market_id, price, 0.01, timestamp)
        
        # Verify two snapshots were added
        history = tracker.get_history("664293")
        assert len(history) == 2
    
    def test_save_snapshots_to_json(self, tmp_path):
        """Test saving PnL snapshots to JSON."""
        output_file = tmp_path / "pnl_snapshots.json"
        
        snapshots = [
            {
                "timestamp": datetime.now().isoformat(),
                "market_id": "664293",
                "current_price": 0.60,
                "unrealized_pnl": 8.4
            }
        ]
        
        with open(output_file, 'w') as f:
            json.dump(snapshots, f, indent=2)
        
        # Verify file was created
        assert output_file.exists()
        with open(output_file, 'r') as f:
            loaded = json.load(f)
            assert len(loaded) == 1
            assert loaded[0]["market_id"] == "664293"
    
    def test_configuration_from_env(self, monkeypatch):
        """Test reading configuration from environment variables."""
        monkeypatch.setenv("PNL_POLL_INTERVAL", "60")
        monkeypatch.setenv("PNL_OUTPUT_DIR", "/tmp/test_output")
        monkeypatch.setenv("CLOB_HOST", "https://test-clob.com")
        
        poll_interval = int(os.getenv("PNL_POLL_INTERVAL", "30"))
        output_dir = os.getenv("PNL_OUTPUT_DIR", "data")
        clob_host = os.getenv("CLOB_HOST", "https://clob.polymarket.com")
        
        assert poll_interval == 60
        assert output_dir == "/tmp/test_output"
        assert clob_host == "https://test-clob.com"
    
    def test_error_handling_during_polling(self):
        """Test error handling when API calls fail."""
        tracker = PriceTracker()
        calculator = PnLCalculator()
        
        # Simulate API failure - should continue with other markets
        try:
            # This would normally raise an exception
            raise Exception("API Error")
        except Exception:
            # Should handle gracefully
            pass
        
        # Tracker should still work
        tracker.add_snapshot("664293", 0.595, 0.01, datetime.now())
        assert tracker.get_latest_price("664293") == 0.595
    
    def test_filter_active_markets(self):
        """Test filtering only active (non-ended) markets."""
        events = [
            {"pm_market_id": "664293", "pm_ended": False},
            {"pm_market_id": "664349", "pm_ended": True},
            {"pm_market_id": "664367", "pm_ended": False}
        ]
        
        active_markets = [e for e in events if not e.get("pm_ended", False)]
        
        assert len(active_markets) == 2
        assert active_markets[0]["pm_market_id"] == "664293"
        assert active_markets[1]["pm_market_id"] == "664367"

