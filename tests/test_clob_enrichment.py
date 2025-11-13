"""Tests for CLOB data enrichment."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from poly_sports.data_fetching.fetch_sports_markets import enrich_market_with_clob_data, enrich_markets_with_clob_data


class TestClobEnrichment:
    """Test CLOB data enrichment functionality."""
    
    def test_enrich_market_with_clob_data_success(self):
        """Test successful enrichment of a market with CLOB data."""
        mock_client = MagicMock()
        market = {
            'id': '1',
            'tokens': [
                {'token_id': '123', 'outcome': 'Yes'},
                {'token_id': '456', 'outcome': 'No'}
            ]
        }
        
        # Mock CLOB client methods
        mock_client.get_midpoint.return_value = {'mid': '0.55'}
        mock_client.get_price.side_effect = [
            {'price': '0.56'},  # BUY price
            {'price': '0.54'}   # SELL price
        ]
        mock_client.get_spread.return_value = {'spread': '0.02'}
        mock_orderbook = MagicMock()
        mock_orderbook.bids = [MagicMock(price='0.55')]
        mock_orderbook.asks = [MagicMock(price='0.57')]
        mock_client.get_order_book.return_value = mock_orderbook
        
        result = enrich_market_with_clob_data(mock_client, market)
        
        assert 'clob_data' in result
        assert result['clob_data']['midpoint'] == '0.55'
        assert result['clob_data']['buy_price'] == '0.56'
        assert result['clob_data']['sell_price'] == '0.54'
        assert result['clob_data']['spread'] == '0.02'
        assert 'order_book' in result['clob_data']
    
    def test_enrich_market_with_clob_data_no_tokens(self):
        """Test enrichment when market has no tokens."""
        mock_client = MagicMock()
        market = {
            'id': '1',
            'tokens': []
        }
        
        result = enrich_market_with_clob_data(mock_client, market)
        
        assert 'clob_data' not in result or result.get('clob_data') is None
    
    def test_enrich_market_with_clob_data_api_error(self):
        """Test handling of CLOB API errors."""
        mock_client = MagicMock()
        market = {
            'id': '1',
            'tokens': [{'token_id': '123', 'outcome': 'Yes'}]
        }
        
        # Mock all API methods to fail
        mock_client.get_midpoint.side_effect = Exception("CLOB API Error")
        mock_client.get_price.side_effect = Exception("CLOB API Error")
        mock_client.get_spread.side_effect = Exception("CLOB API Error")
        mock_client.get_order_book.side_effect = Exception("CLOB API Error")
        
        result = enrich_market_with_clob_data(mock_client, market)
        
        # Should handle error gracefully and return market without CLOB data
        assert 'clob_data' not in result or result.get('clob_data') is None
    
    def test_enrich_market_with_clob_data_partial_failure(self):
        """Test enrichment when some CLOB calls fail."""
        mock_client = MagicMock()
        market = {
            'id': '1',
            'tokens': [{'token_id': '123', 'outcome': 'Yes'}]
        }
        
        # Mock partial success
        mock_client.get_midpoint.return_value = {'mid': '0.55'}
        mock_client.get_price.side_effect = Exception("Price API Error")
        mock_client.get_spread.return_value = {'spread': '0.02'}
        
        result = enrich_market_with_clob_data(mock_client, market)
        
        # Should include what succeeded
        assert 'clob_data' in result
        assert result['clob_data']['midpoint'] == '0.55'
        assert 'buy_price' not in result['clob_data'] or result['clob_data'].get('buy_price') is None
    
    @patch('fetch_sports_markets.ClobClient')
    def test_enrich_markets_with_clob_data_batch(self, mock_clob_client_class):
        """Test enriching multiple markets with CLOB data."""
        mock_client = MagicMock()
        mock_clob_client_class.return_value = mock_client
        
        markets = [
            {
                'id': '1',
                'tokens': [{'token_id': '123', 'outcome': 'Yes'}]
            },
            {
                'id': '2',
                'tokens': [{'token_id': '456', 'outcome': 'Yes'}]
            }
        ]
        
        # Mock CLOB responses
        mock_client.get_midpoint.side_effect = [
            {'mid': '0.55'},
            {'mid': '0.60'}
        ]
        mock_client.get_price.side_effect = [
            {'price': '0.56'},
            {'price': '0.54'},
            {'price': '0.61'},
            {'price': '0.59'}
        ]
        mock_client.get_spread.side_effect = [
            {'spread': '0.02'},
            {'spread': '0.02'}
        ]
        mock_orderbook = MagicMock()
        mock_orderbook.bids = [MagicMock(price='0.55')]
        mock_orderbook.asks = [MagicMock(price='0.57')]
        mock_client.get_order_book.return_value = mock_orderbook
        
        result = enrich_markets_with_clob_data('https://clob.polymarket.com', markets)
        
        assert len(result) == 2
        assert all('clob_data' in market for market in result)
        assert result[0]['clob_data']['midpoint'] == '0.55'
        assert result[1]['clob_data']['midpoint'] == '0.60'

