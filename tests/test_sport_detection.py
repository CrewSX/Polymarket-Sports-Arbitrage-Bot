"""Tests for sport key auto-detection."""
import pytest
from poly_sports.processing.sport_detection import detect_sport_key


class TestSportDetection:
    """Test sport key auto-detection from Polymarket event data."""
    
    def test_detect_nfl_from_series_ticker(self):
        """Test NFL detection from series_ticker."""
        event = {
            'series_ticker': 'nfl',
            'homeTeamName': 'New England Patriots',
            'awayTeamName': 'Kansas City Chiefs',
            'question': 'Who will win?'
        }
        assert detect_sport_key(event) == 'americanfootball_nfl'
    
    def test_detect_nba_from_series_ticker(self):
        """Test NBA detection from series_ticker."""
        event = {
            'series_ticker': 'nba',
            'homeTeamName': 'Los Angeles Lakers',
            'awayTeamName': 'Boston Celtics',
            'question': 'Who will win?'
        }
        assert detect_sport_key(event) == 'basketball_nba'
    
    def test_detect_mlb_from_series_ticker(self):
        """Test MLB detection from series_ticker."""
        event = {
            'series_ticker': 'mlb',
            'homeTeamName': 'New York Yankees',
            'awayTeamName': 'Boston Red Sox',
            'question': 'Who will win?'
        }
        assert detect_sport_key(event) == 'baseball_mlb'
    
    def test_detect_nhl_from_series_ticker(self):
        """Test NHL detection from series_ticker."""
        event = {
            'series_ticker': 'nhl',
            'homeTeamName': 'Boston Bruins',
            'awayTeamName': 'Toronto Maple Leafs',
            'question': 'Who will win?'
        }
        assert detect_sport_key(event) == 'icehockey_nhl'
    
    def test_detect_ncaaf_from_series_ticker(self):
        """Test NCAAF detection from series_ticker."""
        event = {
            'series_ticker': 'ncaaf',
            'homeTeamName': 'Alabama Crimson Tide',
            'awayTeamName': 'Georgia Bulldogs',
            'question': 'Who will win?'
        }
        assert detect_sport_key(event) == 'americanfootball_ncaaf'
    
    def test_detect_ncaab_from_series_ticker(self):
        """Test NCAAB detection from series_ticker."""
        event = {
            'series_ticker': 'ncaab',
            'homeTeamName': 'Duke Blue Devils',
            'awayTeamName': 'North Carolina Tar Heels',
            'question': 'Who will win?'
        }
        assert detect_sport_key(event) == 'basketball_ncaab'
    
    def test_detect_from_team_names_nfl(self):
        """Test NFL detection from team names when ticker is missing."""
        event = {
            'series_ticker': 'unknown',
            'homeTeamName': 'New England Patriots',
            'awayTeamName': 'Kansas City Chiefs',
            'question': 'Who will win?'
        }
        # Should detect NFL from team names
        assert detect_sport_key(event) == 'americanfootball_nfl'
    
    def test_detect_from_team_names_nba(self):
        """Test NBA detection from team names."""
        event = {
            'series_ticker': '',
            'homeTeamName': 'Los Angeles Lakers',
            'awayTeamName': 'Boston Celtics',
            'question': 'Who will win?'
        }
        assert detect_sport_key(event) == 'basketball_nba'
    
    def test_detect_from_team_names_mlb(self):
        """Test MLB detection from team names."""
        event = {
            'series_ticker': None,
            'homeTeamName': 'New York Yankees',
            'awayTeamName': 'Boston Red Sox',
            'question': 'Who will win?'
        }
        assert detect_sport_key(event) == 'baseball_mlb'
    
    def test_detect_from_question_keywords(self):
        """Test detection from keywords in question field."""
        event = {
            'series_ticker': '',
            'homeTeamName': '',
            'awayTeamName': '',
            'question': 'NFL game: Who will win?'
        }
        assert detect_sport_key(event) == 'americanfootball_nfl'
    
    def test_detect_soccer_from_keywords(self):
        """Test soccer detection from keywords."""
        event = {
            'series_ticker': '',
            'homeTeamName': 'Manchester United',
            'awayTeamName': 'Liverpool',
            'question': 'Premier League match'
        }
        # Should detect soccer (may need to check available sport keys)
        result = detect_sport_key(event)
        assert result is not None
        assert 'soccer' in result.lower() or 'football' in result.lower()
    
    def test_detect_mma_from_keywords(self):
        """Test MMA detection from keywords."""
        event = {
            'series_ticker': '',
            'homeTeamName': '',
            'awayTeamName': '',
            'question': 'UFC fight: Who will win?'
        }
        result = detect_sport_key(event)
        assert result == 'mma_mixed_martial_arts' or 'mma' in result.lower()
    
    def test_case_insensitive_ticker(self):
        """Test that ticker detection is case-insensitive."""
        event = {
            'series_ticker': 'NFL',
            'homeTeamName': 'Team A',
            'awayTeamName': 'Team B',
            'question': 'Who will win?'
        }
        assert detect_sport_key(event) == 'americanfootball_nfl'
    
    def test_no_detection_returns_none(self):
        """Test that unknown sports return None."""
        event = {
            'series_ticker': 'unknown_sport',
            'homeTeamName': 'Unknown Team A',
            'awayTeamName': 'Unknown Team B',
            'question': 'Who will win?'
        }
        assert detect_sport_key(event) is None
    
    def test_empty_event_returns_none(self):
        """Test that empty event returns None."""
        event = {}
        assert detect_sport_key(event) is None
    
    def test_missing_fields_handled_gracefully(self):
        """Test that missing fields don't cause errors."""
        event = {
            'series_ticker': 'nfl'
        }
        assert detect_sport_key(event) == 'americanfootball_nfl'
    
    def test_prioritize_ticker_over_team_names(self):
        """Test that series_ticker takes priority over team name detection."""
        event = {
            'series_ticker': 'nba',
            'homeTeamName': 'New England Patriots',  # NFL team name
            'awayTeamName': 'Kansas City Chiefs',   # NFL team name
            'question': 'Who will win?'
        }
        # Should use ticker (NBA) not team names (NFL)
        assert detect_sport_key(event) == 'basketball_nba'

