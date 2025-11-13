"""Tests for real-time price fetching from Polymarket CLOB API."""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from poly_sports.data_fetching.fetch_realtime_prices import (
    extract_market_identifiers,
    parse_token_ids,
    fetch_market_price,
    fetch_market_prices_batch
)
from poly_sports.utils.file_utils import load_json


class TestLoadJson:
    """Test loading events from JSON file."""
    
    def test_load_json_success(self, tmp_path):
        """Test successfully loading events from JSON file."""
        # Create test JSON file
        test_data = [
            {
                "pm_market_id": "664293",
                "pm_conditionId": "0x123",
                "pm_clobTokenIds": '["token1", "token2"]'
            },
            {
                "pm_market_id": "664349",
                "pm_conditionId": "0x456",
                "pm_clobTokenIds": '["token3"]'
            }
        ]
        test_file = tmp_path / "test_events.json"
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        
        result = load_json(str(test_file))
        
        assert len(result) == 2
        assert result[0]["pm_market_id"] == "664293"
        assert result[1]["pm_market_id"] == "664349"
    
    def test_load_json_file_not_found(self):
        """Test handling of missing file."""
        with pytest.raises(FileNotFoundError):
            load_json("nonexistent.json")
    
    def test_load_json_invalid_json(self, tmp_path):
        """Test handling of invalid JSON."""
        test_file = tmp_path / "invalid.json"
        test_file.write_text("not json")
        
        with pytest.raises(json.JSONDecodeError):
            load_json(str(test_file))


class TestExtractMarketIdentifiers:
    """Test extracting market identifiers from events."""
    
    def test_extract_market_identifiers_complete(self):
        """Test extracting all identifiers from complete event."""
        event = {
            "pm_market_id": "664293",
            "pm_conditionId": "0x69968f6c545afe581c4474f4986681a122d986ccde53874c94c0de2846a0804b",
            "pm_clobTokenIds": '["58782268610494854613686357464756193474730417578256543349478088088273599566068", "70189345639847139239611921360046417771400060146785301034047964679574368803466"]',
            "pm_event_id": "72621"
        }
        
        result = extract_market_identifiers(event)
        
        assert result["market_id"] == "664293"
        assert result["condition_id"] == "0x69968f6c545afe581c4474f4986681a122d986ccde53874c94c0de2846a0804b"
        assert result["event_id"] == "72621"
        assert "clob_token_ids" in result
    
    def test_extract_market_identifiers_missing_fields(self):
        """Test extracting with missing optional fields."""
        event = {
            "pm_market_id": "664293"
        }
        
        result = extract_market_identifiers(event)
        
        assert result["market_id"] == "664293"
        assert result.get("condition_id") is None
        assert result.get("event_id") is None


class TestParseTokenIds:
    """Test parsing token IDs from JSON string."""
    
    def test_parse_token_ids_valid_json_string(self):
        """Test parsing valid JSON string of token IDs."""
        token_ids_str = '["58782268610494854613686357464756193474730417578256543349478088088273599566068", "70189345639847139239611921360046417771400060146785301034047964679574368803466"]'
        
        result = parse_token_ids(token_ids_str)
        
        assert len(result) == 2
        assert result[0] == "58782268610494854613686357464756193474730417578256543349478088088273599566068"
        assert result[1] == "70189345639847139239611921360046417771400060146785301034047964679574368803466"
    
    def test_parse_token_ids_empty_string(self):
        """Test parsing empty string."""
        result = parse_token_ids("")
        assert result == []
    
    def test_parse_token_ids_none(self):
        """Test parsing None value."""
        result = parse_token_ids(None)
        assert result == []
    
    def test_parse_token_ids_invalid_json(self):
        """Test handling invalid JSON string."""
        with pytest.raises(json.JSONDecodeError):
            parse_token_ids("not valid json")
    
    def test_parse_token_ids_already_list(self):
        """Test handling when input is already a list."""
        token_ids = ["token1", "token2"]
        result = parse_token_ids(token_ids)
        assert result == token_ids


class TestFetchMarketPrice:
    """Test fetching price for a single market."""
    
    def test_fetch_market_price_success_midpoint(self):
        """Test successfully fetching price using midpoint."""
        mock_client = Mock()
        mock_client.get_midpoint.return_value = {"mid": "0.595"}
        
        result = fetch_market_price(mock_client, "token123")
        
        assert result == 0.595
        mock_client.get_midpoint.assert_called_once_with("token123")
    
    def test_fetch_market_price_fallback_to_buy_price(self):
        """Test fallback to buy price when midpoint unavailable."""
        mock_client = Mock()
        mock_client.get_midpoint.return_value = None
        mock_client.get_price.return_value = {"price": "0.60"}
        
        result = fetch_market_price(mock_client, "token123")
        
        assert result == 0.60
        mock_client.get_midpoint.assert_called_once_with("token123")
        mock_client.get_price.assert_called_once_with("token123", side="BUY")
    
    def test_fetch_market_price_api_error(self):
        """Test handling API errors."""
        mock_client = Mock()
        mock_client.get_midpoint.side_effect = Exception("API Error")
        mock_client.get_price.side_effect = Exception("API Error")
        
        result = fetch_market_price(mock_client, "token123")
        
        assert result is None
    
    def test_fetch_market_price_invalid_response(self):
        """Test handling invalid response format."""
        mock_client = Mock()
        mock_client.get_midpoint.return_value = {"invalid": "data"}
        mock_client.get_price.return_value = None
        
        result = fetch_market_price(mock_client, "token123")
        
        assert result is None


class TestFetchMarketPricesBatch:
    """Test batch fetching prices for multiple markets."""
    
    def test_fetch_market_prices_batch_success(self):
        """Test successfully fetching prices for multiple markets."""
        mock_client = Mock()
        mock_client.get_midpoint.side_effect = [
            {"mid": "0.595"},
            {"mid": "0.405"},
            {"mid": "0.56"}
        ]
        
        markets = [
            {"market_id": "664293", "token_ids": ["token1", "token2"]},
            {"market_id": "664349", "token_ids": ["token3"]}
        ]
        
        result = fetch_market_prices_batch(mock_client, markets)
        
        assert len(result) == 2
        assert result["664293"]["token1"] == 0.595
        assert result["664293"]["token2"] == 0.405
        assert result["664349"]["token3"] == 0.56
    
    def test_fetch_market_prices_batch_partial_failure(self):
        """Test handling partial failures in batch."""
        mock_client = Mock()
        mock_client.get_midpoint.side_effect = [
            {"mid": "0.595"},
            Exception("API Error"),
            {"mid": "0.56"}
        ]
        
        markets = [
            {"market_id": "664293", "token_ids": ["token1", "token2"]},
            {"market_id": "664349", "token_ids": ["token3"]}
        ]
        
        result = fetch_market_prices_batch(mock_client, markets)
        
        assert "664293" in result
        assert result["664293"]["token1"] == 0.595
        assert "token2" not in result["664293"] or result["664293"]["token2"] is None
        assert result["664349"]["token3"] == 0.56
    
    def test_fetch_market_prices_batch_no_token_ids(self):
        """Test handling markets without token IDs."""
        mock_client = Mock()
        
        markets = [
            {"market_id": "664293", "token_ids": []},
            {"market_id": "664349", "token_ids": ["token3"]}
        ]
        
        result = fetch_market_prices_batch(mock_client, markets)
        
        assert "664293" in result
        assert len(result["664293"]) == 0
        assert "664349" in result

