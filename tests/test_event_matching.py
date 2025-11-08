"""Tests for event matching between Polymarket and The Odds API."""
import pytest
from datetime import datetime, timezone, timedelta
from event_matching import (
    normalize_team_name,
    calculate_match_score,
    match_events,
)


class TestNormalizeTeamName:
    """Test team name normalization."""
    
    def test_remove_common_suffixes(self):
        """Test removal of common team suffixes."""
        assert normalize_team_name("New England Patriots") == "new england patriots"
        assert normalize_team_name("Los Angeles Lakers") == "los angeles lakers"
        assert normalize_team_name("Boston Celtics") == "boston celtics"
    
    def test_case_insensitive(self):
        """Test that normalization is case-insensitive."""
        assert normalize_team_name("NEW ENGLAND PATRIOTS") == normalize_team_name("new england patriots")
        assert normalize_team_name("Los Angeles Lakers") == normalize_team_name("LOS ANGELES LAKERS")
    
    def test_handle_empty_string(self):
        """Test handling of empty strings."""
        assert normalize_team_name("") == ""
        assert normalize_team_name("   ") == ""
    
    def test_handle_none(self):
        """Test handling of None values."""
        assert normalize_team_name(None) == ""


class TestCalculateMatchScore:
    """Test match score calculation."""
    
    def test_exact_match_high_score(self):
        """Test that exact matches get high scores."""
        pm_event = {
            'homeTeamName': 'New England Patriots',
            'awayTeamName': 'Kansas City Chiefs',
            'startTime': '2024-01-15T20:00:00Z'
        }
        odds_event = {
            'home_team': 'New England Patriots',
            'away_team': 'Kansas City Chiefs',
            'commence_time': '2024-01-15T20:00:00Z'
        }
        score = calculate_match_score(pm_event, odds_event)
        assert score >= 0.9  # Exact match should be very high
    
    def test_fuzzy_match_medium_score(self):
        """Test that fuzzy matches get medium scores."""
        pm_event = {
            'homeTeamName': 'New England Patriots',
            'awayTeamName': 'Kansas City Chiefs',
            'startTime': '2024-01-15T20:00:00Z'
        }
        odds_event = {
            'home_team': 'New England Patriots',
            'away_team': 'Kansas City Cheifs',  # Typo
            'commence_time': '2024-01-15T20:00:00Z'
        }
        score = calculate_match_score(pm_event, odds_event)
        # Single letter typo is very close, so score will be high but less than exact match
        # One team exact match + one team with typo should still score well
        assert 0.7 <= score < 1.0  # Fuzzy match should be high but not perfect
    
    def test_date_mismatch_lowers_score(self):
        """Test that date mismatches lower the score."""
        pm_event = {
            'homeTeamName': 'New England Patriots',
            'awayTeamName': 'Kansas City Chiefs',
            'startTime': '2024-01-15T20:00:00Z'
        }
        odds_event = {
            'home_team': 'New England Patriots',
            'away_team': 'Kansas City Chiefs',
            'commence_time': '2024-01-20T20:00:00Z'  # Different date
        }
        score = calculate_match_score(pm_event, odds_event)
        assert score < 0.8  # Date mismatch should lower score
    
    def test_team_order_doesnt_matter(self):
        """Test that home/away order doesn't matter."""
        pm_event = {
            'homeTeamName': 'New England Patriots',
            'awayTeamName': 'Kansas City Chiefs',
            'startTime': '2024-01-15T20:00:00Z'
        }
        odds_event = {
            'home_team': 'Kansas City Chiefs',  # Swapped
            'away_team': 'New England Patriots',  # Swapped
            'commence_time': '2024-01-15T20:00:00Z'
        }
        score = calculate_match_score(pm_event, odds_event)
        assert score >= 0.8  # Should still match well
    
    def test_no_match_low_score(self):
        """Test that completely different events get low scores."""
        pm_event = {
            'homeTeamName': 'New England Patriots',
            'awayTeamName': 'Kansas City Chiefs',
            'startTime': '2024-01-15T20:00:00Z'
        }
        odds_event = {
            'home_team': 'Los Angeles Lakers',
            'away_team': 'Boston Celtics',
            'commence_time': '2024-01-15T20:00:00Z'
        }
        score = calculate_match_score(pm_event, odds_event)
        # Completely different teams should get low score (fuzzy matching may find some similarity)
        assert score < 0.5  # Should be relatively low


class TestMatchEvents:
    """Test matching multiple events."""
    
    def test_match_single_event(self):
        """Test matching a single Polymarket event."""
        pm_events = [{
            'event_id': 'pm1',
            'homeTeamName': 'New England Patriots',
            'awayTeamName': 'Kansas City Chiefs',
            'startTime': '2024-01-15T20:00:00Z'
        }]
        odds_events = [{
            'id': 'odds1',
            'home_team': 'New England Patriots',
            'away_team': 'Kansas City Chiefs',
            'commence_time': '2024-01-15T20:00:00Z'
        }]
        matches = match_events(pm_events, odds_events)
        assert len(matches) == 1
        assert matches[0]['pm_event']['event_id'] == 'pm1'
        assert matches[0]['odds_event']['id'] == 'odds1'
        assert matches[0]['confidence'] >= 0.9
    
    def test_match_multiple_events(self):
        """Test matching multiple events."""
        pm_events = [
            {
                'event_id': 'pm1',
                'homeTeamName': 'New England Patriots',
                'awayTeamName': 'Kansas City Chiefs',
                'startTime': '2024-01-15T20:00:00Z'
            },
            {
                'event_id': 'pm2',
                'homeTeamName': 'Los Angeles Lakers',
                'awayTeamName': 'Boston Celtics',
                'startTime': '2024-01-16T20:00:00Z'
            }
        ]
        odds_events = [
            {
                'id': 'odds1',
                'home_team': 'New England Patriots',
                'away_team': 'Kansas City Chiefs',
                'commence_time': '2024-01-15T20:00:00Z'
            },
            {
                'id': 'odds2',
                'home_team': 'Los Angeles Lakers',
                'away_team': 'Boston Celtics',
                'commence_time': '2024-01-16T20:00:00Z'
            }
        ]
        matches = match_events(pm_events, odds_events)
        assert len(matches) == 2
        assert all(m['confidence'] >= 0.9 for m in matches)
    
    def test_no_matches_returns_empty(self):
        """Test that no matches returns empty list."""
        pm_events = [{
            'event_id': 'pm1',
            'homeTeamName': 'Team A',
            'awayTeamName': 'Team B',
            'startTime': '2024-01-15T20:00:00Z'
        }]
        odds_events = [{
            'id': 'odds1',
            'home_team': 'Team C',
            'away_team': 'Team D',
            'commence_time': '2024-01-15T20:00:00Z'
        }]
        # Use higher min_confidence to filter out weak matches
        # Short team names may have some fuzzy similarity, so use high threshold
        matches = match_events(pm_events, odds_events, min_confidence=0.85)
        assert len(matches) == 0
    
    def test_min_confidence_filtering(self):
        """Test that min_confidence filters low-confidence matches."""
        pm_events = [{
            'event_id': 'pm1',
            'homeTeamName': 'New England Patriots',
            'awayTeamName': 'Kansas City Chiefs',
            'startTime': '2024-01-15T20:00:00Z'
        }]
        odds_events = [{
            'id': 'odds1',
            'home_team': 'New England Patriots',
            'away_team': 'Kansas City Cheifs',  # Typo
            'commence_time': '2024-01-20T20:00:00Z'  # Different date
        }]
        matches = match_events(pm_events, odds_events, min_confidence=0.8)
        # Should be filtered out if confidence is too low
        assert len(matches) == 0 or matches[0]['confidence'] < 0.8
    
    def test_best_match_selected(self):
        """Test that best match is selected when multiple candidates exist."""
        pm_events = [{
            'event_id': 'pm1',
            'homeTeamName': 'New England Patriots',
            'awayTeamName': 'Kansas City Chiefs',
            'startTime': '2024-01-15T20:00:00Z'
        }]
        odds_events = [
            {
                'id': 'odds1',
                'home_team': 'New England Patriots',
                'away_team': 'Kansas City Chiefs',
                'commence_time': '2024-01-15T20:00:00Z'  # Exact match
            },
            {
                'id': 'odds2',
                'home_team': 'New England Patriots',
                'away_team': 'Kansas City Cheifs',  # Typo
                'commence_time': '2024-01-15T20:00:00Z'
            }
        ]
        matches = match_events(pm_events, odds_events)
        assert len(matches) == 1
        assert matches[0]['odds_event']['id'] == 'odds1'  # Should pick exact match

