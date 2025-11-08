"""Event matching between Polymarket and The Odds API events."""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dateutil import parser as date_parser
from rapidfuzz import fuzz


def normalize_team_name(name: Optional[str]) -> str:
    """
    Normalize team name for comparison.
    
    - Convert to lowercase
    - Strip whitespace
    - Handle None/empty values
    
    Args:
        name: Team name string or None
        
    Returns:
        Normalized team name string
    """
    if not name:
        return ""
    return str(name).lower().strip()


def calculate_match_score(pm_event: Dict[str, Any], odds_event: Dict[str, Any]) -> float:
    """
    Calculate matching confidence score between Polymarket and Odds API events.
    
    Score is based on:
    - Team name similarity (exact match = 1.0, fuzzy match = 0.5-0.9)
    - Date proximity (within 24 hours = full score, further = reduced)
    
    Args:
        pm_event: Polymarket event dictionary with homeTeamName, awayTeamName, startTime
        odds_event: The Odds API event dictionary with home_team, away_team, commence_time
        
    Returns:
        Confidence score between 0.0 and 1.0
    """
    # Normalize team names
    pm_home = normalize_team_name(pm_event.get('homeTeamName', ''))
    pm_away = normalize_team_name(pm_event.get('awayTeamName', ''))
    odds_home = normalize_team_name(odds_event.get('home_team', ''))
    odds_away = normalize_team_name(odds_event.get('away_team', ''))
    
    # Check for exact matches first
    exact_match1 = (pm_home == odds_home and pm_away == odds_away)
    exact_match2 = (pm_home == odds_away and pm_away == odds_home)
    
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
    try:
        pm_time_str = pm_event.get('startTime') or pm_event.get('eventDate', '')
        odds_time_str = odds_event.get('commence_time', '')
        
        if pm_time_str and odds_time_str:
            pm_time = date_parser.parse(pm_time_str)
            odds_time = date_parser.parse(odds_time_str)
            
            # Calculate time difference in hours
            time_diff = abs((pm_time - odds_time).total_seconds() / 3600)
            
            # Score decreases with time difference
            # Within 24 hours: full score
            # Beyond 24 hours: linear decrease to 0 at 7 days
            if time_diff <= 24:
                date_score = 1.0
            elif time_diff <= 168:  # 7 days
                date_score = 1.0 - ((time_diff - 24) / 144)  # Linear decrease
            else:
                date_score = 0.0
    except (ValueError, TypeError, AttributeError):
        # If date parsing fails, don't penalize (assume dates match)
        date_score = 1.0
    
    # Combined score: 70% team similarity, 30% date proximity
    final_score = (team_similarity * 0.7) + (date_score * 0.3)
    
    return final_score


def match_events(
    polymarket_events: List[Dict[str, Any]],
    odds_api_events: List[Dict[str, Any]],
    min_confidence: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Match Polymarket events to The Odds API events.
    
    For each Polymarket event, finds the best matching Odds API event based on:
    - Team name similarity (exact or fuzzy)
    - Date proximity
    
    Args:
        polymarket_events: List of Polymarket event dictionaries
        odds_api_events: List of The Odds API event dictionaries
        min_confidence: Minimum confidence score to include a match (default: 0.5)
        
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

