"""Tests for The Odds API client."""
import pytest
from unittest.mock import Mock, patch
import requests
from fetch_odds_api import (
    fetch_sports_list,
    fetch_odds,
    fetch_event_odds,
)


class TestFetchSportsList:
    """Test fetching sports list from The Odds API."""
    
    @patch('fetch_odds_api.requests.get')
    def test_fetch_sports_list_success(self, mock_get):
        """Test successful fetching of sports list."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'key': 'americanfootball_nfl',
                'group': 'American Football',
                'title': 'NFL',
                'description': 'US Football',
                'active': True,
                'has_outrights': False
            },
            {
                'key': 'basketball_nba',
                'group': 'Basketball',
                'title': 'NBA',
                'description': 'US Basketball',
                'active': True,
                'has_outrights': False
            }
        ]
        mock_response.headers = {
            'x-requests-remaining': '100',
            'x-requests-used': '0',
            'x-requests-last': '0'
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = fetch_sports_list('test_api_key')
        
        assert len(result) == 2
        assert result[0]['key'] == 'americanfootball_nfl'
        assert result[1]['key'] == 'basketball_nba'
        mock_get.assert_called_once()
    
    @patch('fetch_odds_api.requests.get')
    def test_fetch_sports_list_api_error(self, mock_get):
        """Test handling of API errors."""
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        with pytest.raises(requests.exceptions.RequestException):
            fetch_sports_list('test_api_key')
    
    @patch('fetch_odds_api.requests.get')
    def test_fetch_sports_list_empty_response(self, mock_get):
        """Test handling of empty response."""
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.headers = {}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = fetch_sports_list('test_api_key')
        assert result == []


class TestFetchOdds:
    """Test fetching odds from The Odds API."""
    
    @patch('fetch_odds_api.requests.get')
    def test_fetch_odds_success(self, mock_get):
        """Test successful fetching of odds."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'id': 'event1',
                'sport_key': 'americanfootball_nfl',
                'commence_time': '2024-01-15T20:00:00Z',
                'home_team': 'New England Patriots',
                'away_team': 'Kansas City Chiefs',
                'bookmakers': [
                    {
                        'key': 'fanduel',
                        'title': 'FanDuel',
                        'last_update': '2024-01-15T10:00:00Z',
                        'markets': [
                            {
                                'key': 'h2h',
                                'outcomes': [
                                    {'name': 'New England Patriots', 'price': -110},
                                    {'name': 'Kansas City Chiefs', 'price': -110}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
        mock_response.headers = {
            'x-requests-remaining': '99',
            'x-requests-used': '1',
            'x-requests-last': '1'
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = fetch_odds('americanfootball_nfl', 'test_api_key', regions=['us'], markets=['h2h'])
        
        assert len(result) == 1
        assert result[0]['id'] == 'event1'
        assert len(result[0]['bookmakers']) == 1
        assert result[0]['bookmakers'][0]['key'] == 'fanduel'
    
    @patch('fetch_odds_api.requests.get')
    def test_fetch_odds_with_decimal_format(self, mock_get):
        """Test fetching odds with decimal format."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'id': 'event1',
                'sport_key': 'basketball_nba',
                'commence_time': '2024-01-16T20:00:00Z',
                'home_team': 'Los Angeles Lakers',
                'away_team': 'Boston Celtics',
                'bookmakers': [
                    {
                        'key': 'draftkings',
                        'title': 'DraftKings',
                        'last_update': '2024-01-16T10:00:00Z',
                        'markets': [
                            {
                                'key': 'h2h',
                                'outcomes': [
                                    {'name': 'Los Angeles Lakers', 'price': 1.91},
                                    {'name': 'Boston Celtics', 'price': 1.91}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
        mock_response.headers = {}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = fetch_odds('basketball_nba', 'test_api_key', regions=['us'], markets=['h2h'], odds_format='decimal')
        
        assert len(result) == 1
        assert result[0]['bookmakers'][0]['markets'][0]['outcomes'][0]['price'] == 1.91
    
    @patch('fetch_odds_api.requests.get')
    def test_fetch_odds_api_error(self, mock_get):
        """Test handling of API errors."""
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        with pytest.raises(requests.exceptions.RequestException):
            fetch_odds('americanfootball_nfl', 'test_api_key', regions=['us'], markets=['h2h'])


class TestFetchEventOdds:
    """Test fetching odds for a specific event."""
    
    @patch('fetch_odds_api.requests.get')
    def test_fetch_event_odds_success(self, mock_get):
        """Test successful fetching of event odds."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': 'event1',
            'sport_key': 'americanfootball_nfl',
            'commence_time': '2024-01-15T20:00:00Z',
            'home_team': 'New England Patriots',
            'away_team': 'Kansas City Chiefs',
            'bookmakers': [
                {
                    'key': 'fanduel',
                    'title': 'FanDuel',
                    'last_update': '2024-01-15T10:00:00Z',
                    'markets': [
                        {
                            'key': 'h2h',
                            'outcomes': [
                                {'name': 'New England Patriots', 'price': -110},
                                {'name': 'Kansas City Chiefs', 'price': -110}
                            ]
                        }
                    ]
                }
            ]
        }
        mock_response.headers = {
            'x-requests-remaining': '98',
            'x-requests-used': '2',
            'x-requests-last': '1'
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = fetch_event_odds('event1', 'americanfootball_nfl', 'test_api_key', regions=['us'], markets=['h2h'])
        
        assert result['id'] == 'event1'
        assert len(result['bookmakers']) == 1
    
    @patch('fetch_odds_api.requests.get')
    def test_fetch_event_odds_not_found(self, mock_get):
        """Test handling of event not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        # The function wraps HTTPError in RequestException
        with pytest.raises(requests.exceptions.RequestException):
            fetch_event_odds('nonexistent', 'americanfootball_nfl', 'test_api_key', regions=['us'], markets=['h2h'])

