"""Tests for main odds data integration."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fetch_odds_data import fetch_odds_for_polymarket_events
from odds_utils import american_to_decimal, american_to_implied_prob


class TestFetchOddsForPolymarketEvents:
    """Test main integration function."""
    
    @patch('fetch_odds_data.fetch_odds')
    @patch('fetch_odds_data.detect_sport_key')
    @patch('fetch_odds_data.match_events')
    def test_fetch_odds_success(self, mock_match, mock_detect, mock_fetch_odds):
        """Test successful fetching and matching of odds."""
        # Mock Polymarket events
        pm_events = [
            {
                'event_id': 'pm1',
                'homeTeamName': 'New England Patriots',
                'awayTeamName': 'Kansas City Chiefs',
                'startTime': '2024-01-15T20:00:00Z',
                'series_ticker': 'nfl',
                'market_outcomes': '["New England Patriots", "Kansas City Chiefs"]',
                'market_outcomePrices': '["0.45", "0.55"]'
            }
        ]
        
        # Mock sport detection
        mock_detect.return_value = 'americanfootball_nfl'
        
        # Mock Odds API response
        mock_odds_events = [
            {
                'id': 'odds1',
                'home_team': 'New England Patriots',
                'away_team': 'Kansas City Chiefs',
                'commence_time': '2024-01-15T20:00:00Z',
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
        mock_fetch_odds.return_value = mock_odds_events
        
        # Mock event matching
        mock_match.return_value = [
            {
                'pm_event': pm_events[0],
                'odds_event': mock_odds_events[0],
                'confidence': 0.95
            }
        ]
        
        result = fetch_odds_for_polymarket_events(pm_events, 'test_api_key')
        
        assert len(result) == 1
        assert result[0]['pm_event_id'] == 'pm1'  # Fields are prefixed with 'pm_'
        assert result[0]['odds_api_event_id'] == 'odds1'
        assert result[0]['odds_api_sport_key'] == 'americanfootball_nfl'
        assert result[0]['match_confidence'] == 0.95
        assert len(result[0]['bookmakers']) == 1
        assert result[0]['bookmakers'][0]['bookmaker_key'] == 'fanduel'
    
    @patch('fetch_odds_data.fetch_odds')
    @patch('fetch_odds_data.detect_sport_key')
    @patch('fetch_odds_data.match_events')
    def test_multiple_events_multiple_bookmakers(self, mock_match, mock_detect, mock_fetch_odds):
        """Test handling multiple events with multiple bookmakers."""
        pm_events = [
            {
                'event_id': 'pm1',
                'homeTeamName': 'New England Patriots',
                'awayTeamName': 'Kansas City Chiefs',
                'startTime': '2024-01-15T20:00:00Z',
                'series_ticker': 'nfl'
            }
        ]
        
        mock_detect.return_value = 'americanfootball_nfl'
        
        mock_odds_events = [
            {
                'id': 'odds1',
                'home_team': 'New England Patriots',
                'away_team': 'Kansas City Chiefs',
                'commence_time': '2024-01-15T20:00:00Z',
                'bookmakers': [
                    {
                        'key': 'fanduel',
                        'title': 'FanDuel',
                        'last_update': '2024-01-15T10:00:00Z',
                        'markets': [{'key': 'h2h', 'outcomes': []}]
                    },
                    {
                        'key': 'draftkings',
                        'title': 'DraftKings',
                        'last_update': '2024-01-15T10:00:00Z',
                        'markets': [{'key': 'h2h', 'outcomes': []}]
                    }
                ]
            }
        ]
        mock_fetch_odds.return_value = mock_odds_events
        
        mock_match.return_value = [
            {
                'pm_event': pm_events[0],
                'odds_event': mock_odds_events[0],
                'confidence': 0.95
            }
        ]
        
        result = fetch_odds_for_polymarket_events(pm_events, 'test_api_key')
        
        # Should have one match with two bookmakers
        assert len(result) == 1
        assert len(result[0]['bookmakers']) == 2
    
    @patch('fetch_odds_data.fetch_odds')
    @patch('fetch_odds_data.detect_sport_key')
    @patch('fetch_odds_data.match_events')
    def test_no_sport_detection_skips_event(self, mock_match, mock_detect, mock_fetch_odds):
        """Test that events without sport detection are skipped."""
        pm_events = [
            {
                'event_id': 'pm1',
                'homeTeamName': 'Unknown Team A',
                'awayTeamName': 'Unknown Team B',
                'startTime': '2024-01-15T20:00:00Z',
                'series_ticker': 'unknown'
            }
        ]
        
        mock_detect.return_value = None  # Cannot detect sport
        
        result = fetch_odds_for_polymarket_events(pm_events, 'test_api_key')
        
        # Should skip events without sport detection
        assert len(result) == 0
        mock_fetch_odds.assert_not_called()
    
    @patch('fetch_odds_data.fetch_odds')
    @patch('fetch_odds_data.detect_sport_key')
    @patch('fetch_odds_data.match_events')
    def test_no_matches_returns_empty(self, mock_match, mock_detect, mock_fetch_odds):
        """Test that events without matches are not included."""
        pm_events = [
            {
                'event_id': 'pm1',
                'homeTeamName': 'New England Patriots',
                'awayTeamName': 'Kansas City Chiefs',
                'startTime': '2024-01-15T20:00:00Z',
                'series_ticker': 'nfl'
            }
        ]
        
        mock_detect.return_value = 'americanfootball_nfl'
        mock_fetch_odds.return_value = []
        mock_match.return_value = []  # No matches
        
        result = fetch_odds_for_polymarket_events(pm_events, 'test_api_key')
        
        assert len(result) == 0
    
    @patch('fetch_odds_data.fetch_odds')
    @patch('fetch_odds_data.detect_sport_key')
    @patch('fetch_odds_data.match_events')
    def test_odds_format_conversion(self, mock_match, mock_detect, mock_fetch_odds):
        """Test that odds are converted to all formats."""
        pm_events = [
            {
                'event_id': 'pm1',
                'homeTeamName': 'New England Patriots',
                'awayTeamName': 'Kansas City Chiefs',
                'startTime': '2024-01-15T20:00:00Z',
                'series_ticker': 'nfl'
            }
        ]
        
        mock_detect.return_value = 'americanfootball_nfl'
        
        mock_odds_events = [
            {
                'id': 'odds1',
                'home_team': 'New England Patriots',
                'away_team': 'Kansas City Chiefs',
                'commence_time': '2024-01-15T20:00:00Z',
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
        mock_fetch_odds.return_value = mock_odds_events
        
        mock_match.return_value = [
            {
                'pm_event': pm_events[0],
                'odds_event': mock_odds_events[0],
                'confidence': 0.95
            }
        ]
        
        result = fetch_odds_for_polymarket_events(pm_events, 'test_api_key')
        
        # Check that odds are converted to all formats
        outcome = result[0]['bookmakers'][0]['markets'][0]['outcomes'][0]
        assert 'price_american' in outcome
        assert 'price_decimal' in outcome
        assert 'implied_probability' in outcome
        assert outcome['price_american'] == -110
        assert outcome['price_decimal'] == pytest.approx(american_to_decimal(-110), rel=1e-6)
        assert outcome['implied_probability'] == pytest.approx(american_to_implied_prob(-110), rel=1e-6)

