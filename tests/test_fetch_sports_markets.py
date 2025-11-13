"""Tests for Gamma API integration and sports market fetching."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from poly_sports.data_fetching.fetch_sports_markets import fetch_sports_markets, filter_sports_markets


class TestFetchSportsMarkets:
    """Test Gamma API integration for fetching sports markets."""
    
    @patch('fetch_sports_markets.requests.get')
    def test_fetch_sports_markets_success(self, mock_get):
        """Test successful fetching of sports markets."""
        # Mock API response - events endpoint returns a list directly
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'id': 'event1',
                'title': 'Event 1',
                'slug': 'event-1',
                'tags': [{'label': 'Sports'}],
                'markets': [
                    {
                        'id': '1',
                        'question': 'Will Team A win?',
                        'tokens': [{'token_id': '123'}],
                        'endDateIso': '2024-12-31T00:00:00Z'
                    },
                    {
                        'id': '2',
                        'question': 'Will Player X score?',
                        'tokens': [{'token_id': '789'}],
                        'endDateIso': '2024-12-31T00:00:00Z'
                    }
                ]
            }
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = fetch_sports_markets('https://gamma-api.polymarket.com')
        
        assert len(result) == 2
        assert result[0]['id'] == '1'
        assert result[1]['id'] == '2'
        assert result[0]['event_id'] == 'event1'
        assert result[0]['event_title'] == 'Event 1'
        mock_get.assert_called_once()
    
    @patch('fetch_sports_markets.requests.get')
    def test_fetch_sports_markets_large_result_set(self, mock_get):
        """Test fetching markets with a large result set."""
        # Events endpoint returns all results in one request
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'id': f'event{i}',
                'title': f'Event {i}',
                'slug': f'event-{i}',
                'tags': [],
                'markets': [
                    {
                        'id': str(i),
                        'question': f'Will Team {i} win?',
                        'tokens': [{'token_id': str(i * 100)}],
                        'endDateIso': '2024-12-31T00:00:00Z'
                    }
                ]
            }
            for i in range(150)  # 150 events with 1 market each = 150 markets
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = fetch_sports_markets('https://gamma-api.polymarket.com', limit=1500)
        
        assert len(result) == 150
        assert mock_get.call_count == 1
    
    @patch('fetch_sports_markets.requests.get')
    def test_fetch_sports_markets_no_sports_markets(self, mock_get):
        """Test when no events/markets are found."""
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = fetch_sports_markets('https://gamma-api.polymarket.com')
        
        assert len(result) == 0
    
    @patch('fetch_sports_markets.requests.get')
    def test_fetch_sports_markets_api_error(self, mock_get):
        """Test handling of API errors."""
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        with pytest.raises(requests.exceptions.RequestException):
            fetch_sports_markets('https://gamma-api.polymarket.com')
    
    @patch('fetch_sports_markets.requests.get')
    def test_fetch_sports_markets_extracts_from_events(self, mock_get):
        """Test that markets are correctly extracted from events."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'id': 'event1',
                'title': 'Sports Event 1',
                'slug': 'sports-event-1',
                'tags': [{'label': 'Sports'}],
                'markets': [
                    {
                        'id': '1',
                        'question': 'Will Team A win?',
                        'tokens': [{'token_id': '123'}],
                        'endDateIso': '2024-12-31T00:00:00Z'
                    },
                    {
                        'id': '2',
                        'question': 'Will Team B win?',
                        'tokens': [{'token_id': '456'}],
                        'endDateIso': '2024-12-31T00:00:00Z'
                    }
                ]
            },
            {
                'id': 'event2',
                'title': 'Sports Event 2',
                'slug': 'sports-event-2',
                'tags': [{'label': 'Sports'}],
                'markets': [
                    {
                        'id': '3',
                        'question': 'Will Team C win?',
                        'tokens': [{'token_id': '789'}],
                        'endDateIso': '2024-12-31T00:00:00Z'
                    }
                ]
            }
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = fetch_sports_markets('https://gamma-api.polymarket.com')
        
        assert len(result) == 3
        assert result[0]['event_id'] == 'event1'
        assert result[2]['event_id'] == 'event2'
        assert result[0]['event_title'] == 'Sports Event 1'


class TestFilterSportsMarkets:
    """Test filtering markets by sports category."""
    
    def test_filter_sports_markets(self):
        """Test filtering markets by sports category."""
        markets = [
            {'id': '1', 'category': 'Sports', 'question': 'Test 1'},
            {'id': '2', 'category': 'Weather', 'question': 'Test 2'},
            {'id': '3', 'category': 'Sports', 'question': 'Test 3'},
            {'id': '4', 'category': 'Politics', 'question': 'Test 4'},
        ]
        
        result = filter_sports_markets(markets)
        
        assert len(result) == 2
        assert result[0]['id'] == '1'
        assert result[1]['id'] == '3'
    
    def test_filter_sports_markets_case_insensitive(self):
        """Test that filtering is case-insensitive."""
        markets = [
            {'id': '1', 'category': 'sports', 'question': 'Test 1'},
            {'id': '2', 'category': 'SPORTS', 'question': 'Test 2'},
            {'id': '3', 'category': 'Sports', 'question': 'Test 3'},
            {'id': '4', 'category': 'Weather', 'question': 'Test 4'},
        ]
        
        result = filter_sports_markets(markets)
        
        assert len(result) == 3
    
    def test_filter_sports_markets_empty_list(self):
        """Test filtering empty market list."""
        result = filter_sports_markets([])
        assert len(result) == 0
    
    def test_filter_sports_markets_no_category_field(self):
        """Test handling markets without category field."""
        markets = [
            {'id': '1', 'question': 'Test 1'},
            {'id': '2', 'category': 'Sports', 'question': 'Test 2'},
        ]
        
        result = filter_sports_markets(markets)
        
        assert len(result) == 1
        assert result[0]['id'] == '2'

