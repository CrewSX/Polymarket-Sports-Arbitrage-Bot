"""Event matching between Polymarket and The Odds API events."""
import json
from typing import List, Dict, Any, Optional, Tuple, Callable
from datetime import datetime, timezone
from dateutil import parser as date_parser
from rapidfuzz import fuzz
from poly_sports.processing.sport_detection import detect_sport_key
from poly_sports.processing.extractors import get_team_name_extractor
from poly_sports.processing.extractors.utils import normalize_team_name


def calculate_match_score(pm_event: Dict[str, Any], odds_event: Dict[str, Any]) -> float:
    """
    Calculate matching confidence score between Polymarket and Odds API events.
    
    Score is based on:
    - Team name similarity (exact match = 1.0, fuzzy match = 0.5-0.9)
    - Date has to be the same day
    
    Args:
        pm_event: Polymarket event dictionary with homeTeamName, awayTeamName, startTime
        odds_event: The Odds API event dictionary with home_team, away_team, commence_time
        
    Returns:
        Confidence score between 0.0 and 1.0
    """
    # First, check if sports match - if not, return 0.0 immediately
    pm_sport_key = detect_sport_key(pm_event)
    odds_sport_key = odds_event.get('sport_key', '')
    
    if pm_sport_key and odds_sport_key:
        if pm_sport_key != odds_sport_key:
            return 0.0
    
    # Get the appropriate extractor based on series_ticker
    series_ticker = pm_event.get('series_ticker', '')
    extractor = get_team_name_extractor(series_ticker)
    
    # Extract team names using the sport-specific extractor
    pm_home, pm_away = extractor.extract_team_names(pm_event)
    
    # If extraction failed (empty strings), return 0.0
    if not pm_home or not pm_away:
        return 0.0
        
    odds_home = normalize_team_name(odds_event.get('home_team', ''))
    odds_away = normalize_team_name(odds_event.get('away_team', ''))
    if series_ticker == 'ufc':
        odds_home = normalize_team_name(odds_event.get('home_team', '')).split()[-1]
        odds_away = normalize_team_name(odds_event.get('away_team', '')).split()[-1]
        pm_home = pm_home.split()[-1]
        pm_away = pm_away.split()[-1]
    
    # Check for exact or subset matches first
    exact_match1 = (pm_home in odds_home and pm_away in odds_away)
    exact_match2 = (pm_home in odds_away and pm_away in odds_home)
    
    if exact_match1 or exact_match2:
        team_similarity = 1.0
    else:
        # Calculate team name similarity using fuzzy matching
        # Try both orders (home/away and swapped)
        similarity1 = (
            fuzz.ratio(pm_home, odds_home) + fuzz.ratio(pm_away, odds_away)
        ) / 200.0
        
        similarity2 = (
            fuzz.ratio(pm_home, odds_away) + fuzz.ratio(pm_away, odds_home)
        ) / 200.0
        
        team_similarity = max(similarity1, similarity2)
        
        # Penalize fuzzy matches more aggressively
        # If similarity is below 80%, reduce score significantly
        if team_similarity < 0.8:
            team_similarity = team_similarity * 0.6  # Reduce by 40%
        elif team_similarity < 0.95:
            team_similarity = team_similarity * 0.85  # Reduce by 15%
    
    # Calculate date similarity
    date_score = 1.0
    pm_time_str = pm_event.get('eventDate', '')
    pm_time_str2 = pm_event.get('startTime', '')
    odds_time_str = odds_event.get('commence_time', '')
    
    if (pm_time_str or pm_time_str2) and odds_time_str:
        pm_date = date_parser.parse(pm_time_str).date()
        pm_date2 = date_parser.parse(pm_time_str2).date()
        odds_date = date_parser.parse(odds_time_str).date()

        if pm_date == odds_date or pm_date2 == odds_date:
            date_score = 1.0
        else:
            date_score = 0.0
    
    return team_similarity * date_score

def match_events(
    polymarket_events: List[Dict[str, Any]],
    odds_api_events: List[Dict[str, Any]],
    min_confidence: float = 0.8
) -> List[Dict[str, Any]]:
    """
    Match Polymarket events to The Odds API events.
    
    For each Polymarket event, finds the best matching Odds API event based on:
    - Team name similarity (exact or fuzzy)
    - Date proximity
    
    Args:
        polymarket_events: List of Polymarket event dictionaries
        odds_api_events: List of The Odds API event dictionaries
        min_confidence: Minimum confidence score to include a match (default: 0.8)
        
    Returns:
        List of match dictionaries, each containing:
        - pm_event: Original Polymarket event
        - odds_event: Matched Odds API event
        - confidence: Match confidence score (0-1)
    """
    matches = []
    
    for pm_event in polymarket_events:
        best_match = None
        best_score = 0.0
        
        for odds_event in odds_api_events:
            score = calculate_match_score(pm_event, odds_event)
            
            if score > best_score:
                best_score = score
                best_match = odds_event
        
        # Only include matches above minimum confidence
        if best_match and best_score >= min_confidence:
            matches.append({
                'pm_event': pm_event,
                'odds_event': best_match,
                'confidence': best_score
            })
    
    return matches

