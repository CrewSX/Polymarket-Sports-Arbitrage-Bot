"""Integration tests for end-to-end flow."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import json
import csv
import tempfile
from poly_sports.data_fetching.fetch_sports_markets import main


class TestIntegration:
    """Test end-to-end integration."""
    
    @patch('poly_sports.data_fetching.fetch_sports_markets.fetch_sports_markets')
    @patch('poly_sports.data_fetching.fetch_sports_markets.enrich_markets_with_clob_data')
    @patch('poly_sports.utils.file_utils.save_json')
    @patch('poly_sports.data_fetching.fetch_sports_markets.save_to_csv')
    @patch.dict(os.environ, {
        'GAMMA_API_URL': 'https://gamma-api.polymarket.com',
        'ENRICH_WITH_CLOB': 'false'
    })
    def test_main_flow_without_clob(self, mock_save_csv, mock_save_json, 
                                      mock_enrich, mock_fetch):
        """Test main flow without CLOB enrichment."""
        # Mock market data
        mock_markets = [
            {
                'id': '1',
                'question': 'Will Team A win?',
                'category': 'Sports',
                'tokens': [{'token_id': '123'}],
                'end_date_iso': '2024-12-31T00:00:00Z'
            },
            {
                'id': '2',
                'question': 'Will Player B score?',
                'category': 'Sports',
                'tokens': [{'token_id': '456'}],
                'end_date_iso': '2024-12-31T00:00:00Z'
            }
        ]
        
        mock_fetch.return_value = mock_markets
        
        main()
        
        # Verify calls
        mock_fetch.assert_called_once()
        mock_enrich.assert_not_called()
        mock_save_json.assert_called_once()
        mock_save_csv.assert_called_once()
        
        # Verify saved data
        json_call_args = mock_save_json.call_args[0]
        csv_call_args = mock_save_csv.call_args[0]
        
        assert len(json_call_args[0]) == 2
        assert len(csv_call_args[0]) == 2
    
    @patch('poly_sports.data_fetching.fetch_sports_markets.fetch_sports_markets')
    @patch('poly_sports.data_fetching.fetch_sports_markets.enrich_markets_with_clob_data')
    @patch('poly_sports.utils.file_utils.save_json')
    @patch('poly_sports.data_fetching.fetch_sports_markets.save_to_csv')
    @patch.dict(os.environ, {
        'GAMMA_API_URL': 'https://gamma-api.polymarket.com',
        'ENRICH_WITH_CLOB': 'true',
        'CLOB_HOST': 'https://clob.polymarket.com'
    })
    def test_main_flow_with_clob(self, mock_save_csv, mock_save_json,
                                  mock_enrich, mock_fetch):
        """Test main flow with CLOB enrichment."""
        mock_markets = [
            {
                'id': '1',
                'question': 'Will Team A win?',
                'category': 'Sports',
                'tokens': [{'token_id': '123'}],
                'end_date_iso': '2024-12-31T00:00:00Z'
            }
        ]
        
        enriched_markets = [
            {
                'id': '1',
                'question': 'Will Team A win?',
                'category': 'Sports',
                'tokens': [{'token_id': '123'}],
                'end_date_iso': '2024-12-31T00:00:00Z',
                'clob_data': {
                    'midpoint': '0.55',
                    'buy_price': '0.56',
                    'sell_price': '0.54'
                }
            }
        ]
        
        mock_fetch.return_value = mock_markets
        mock_enrich.return_value = enriched_markets
        
        main()
        
        # Verify CLOB enrichment was called
        mock_enrich.assert_called_once()
        mock_save_json.assert_called_once()
        mock_save_csv.assert_called_once()
        
        # Verify enriched data was saved
        json_call_args = mock_save_json.call_args[0]
        assert 'clob_data' in json_call_args[0][0]
    
    @patch('poly_sports.data_fetching.fetch_sports_markets.fetch_sports_markets')
    @patch('poly_sports.utils.file_utils.save_json')
    @patch('poly_sports.data_fetching.fetch_sports_markets.save_to_csv')
    @patch.dict(os.environ, {
        'GAMMA_API_URL': 'https://gamma-api.polymarket.com',
        'ENRICH_WITH_CLOB': 'false'
    })
    def test_main_flow_no_sports_markets(self, mock_save_csv, mock_save_json, mock_fetch):
        """Test main flow when no sports markets are found."""
        mock_fetch.return_value = []
        
        main()
        
        # Should still save empty files
        mock_save_json.assert_called_once()
        mock_save_csv.assert_called_once()
        
        json_call_args = mock_save_json.call_args[0]
        assert len(json_call_args[0]) == 0
    
    @patch('poly_sports.data_fetching.fetch_sports_markets.fetch_sports_markets')
    @patch('poly_sports.utils.file_utils.save_json')
    @patch('poly_sports.data_fetching.fetch_sports_markets.save_to_csv')
    @patch.dict(os.environ, {
        'GAMMA_API_URL': 'https://gamma-api.polymarket.com',
        'ENRICH_WITH_CLOB': 'false',
        'OUTPUT_DIR': '/tmp/test_output'
    })
    def test_main_flow_custom_output_dir(self, mock_save_csv, mock_save_json, mock_fetch):
        """Test main flow with custom output directory."""
        mock_markets = [
            {
                'id': '1',
                'question': 'Will Team A win?',
                'category': 'Sports',
                'tokens': [{'token_id': '123'}],
                'end_date_iso': '2024-12-31T00:00:00Z'
            }
        ]
        
        mock_fetch.return_value = mock_markets
        
        main()
        
        # Verify files are saved to custom directory
        json_call_args = mock_save_json.call_args[0]
        csv_call_args = mock_save_csv.call_args[0]
        
        assert '/tmp/test_output' in json_call_args[1] or 'sports_markets.json' in json_call_args[1]
        assert '/tmp/test_output' in csv_call_args[1] or 'sports_markets.csv' in csv_call_args[1]
    
    @patch('poly_sports.data_fetching.fetch_sports_markets.fetch_sports_markets')
    @patch('poly_sports.utils.file_utils.save_json')
    @patch('poly_sports.data_fetching.fetch_sports_markets.save_to_csv')
    @patch.dict(os.environ, {
        'GAMMA_API_URL': 'https://gamma-api.polymarket.com',
        'ENRICH_WITH_CLOB': 'false'
    }, clear=True)
    def test_main_flow_default_env_values(self, mock_save_csv, mock_save_json, mock_fetch):
        """Test main flow with default environment values."""
        mock_markets = [
            {
                'id': '1',
                'question': 'Will Team A win?',
                'category': 'Sports',
                'tokens': [{'token_id': '123'}],
                'end_date_iso': '2024-12-31T00:00:00Z'
            }
        ]
        
        mock_fetch.return_value = mock_markets
        
        main()
        
        # Should use default GAMMA_API_URL
        mock_fetch.assert_called_once()
        assert 'gamma-api.polymarket.com' in mock_fetch.call_args[0][0]

