"""Event matching between Polymarket and The Odds API events."""
import json
from typing import List, Dict, Any, Optional, Tuple, Callable
from datetime import datetime, timezone
from dateutil import parser as date_parser
from rapidfuzz import fuzz
from poly_sports.processing.sport_detection import detect_sport_key


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


def extract_school_names_from_outcomes(pm_event: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract school names from market_outcomes for college football events.
    
    For college football, market_outcomes contains the full school names
    (e.g., "Temple", "Army", "SMU Mustangs", "Boston College") which are
    more accurate than the team names alone.
    
    Args:
        pm_event: Polymarket event dictionary with market_outcomes and series_ticker
        
    Returns:
        Tuple of (home_school_name, away_school_name) or (None, None) if not applicable
    """
    # Check if this is a college football event
    series_ticker = str(pm_event.get('series_ticker', '')).lower()
    if not ('cfb' in series_ticker or 'ncaaf' in series_ticker or 'cwbb' in series_ticker):
        return (None, None)
    
    # Parse market_outcomes JSON string
    market_outcomes_str = pm_event.get('market_outcomes', '')
    if not market_outcomes_str:
        return (None, None)
    
    try:
        if isinstance(market_outcomes_str, str):
            outcomes = json.loads(market_outcomes_str)
        else:
            outcomes = market_outcomes_str
        
        if not isinstance(outcomes, list) or len(outcomes) < 2:
            return (None, None)
        
        # For college football, outcomes typically contain school names
        # Return both outcomes (order may vary, matching logic will handle it)
        return (outcomes[0], outcomes[1])
    except (json.JSONDecodeError, TypeError, IndexError):
        return (None, None)


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
    # First, check if sports match - if not, return 0.0 immediately
    pm_sport_key = detect_sport_key(pm_event)
    odds_sport_key = odds_event.get('sport_key', '')
    
    if pm_sport_key and odds_sport_key:
        if pm_sport_key != odds_sport_key:
            return 0.0
    
    # For college football, use school names from market_outcomes instead of team names
    # This is more accurate since team names can be duplicates (e.g., "Tigers", "Bulldogs")
    school_home, school_away = extract_school_names_from_outcomes(pm_event)
    
    if school_home and school_away:
        # Use school names from market_outcomes for college football
        # The order of market_outcomes may not match homeTeamName/awayTeamName order,
        # so we use school names directly and let fuzzy matching try both orders
        pm_home = normalize_team_name(school_home)
        pm_away = normalize_team_name(school_away)
    else:
        # Use regular team names for other sports
        # Try market_outcomes first, fallback to homeTeamName/awayTeamName if outcomes are "Yes"/"No"
        try:
            outcomes = json.loads(pm_event.get('market_outcomes', '')) if isinstance(pm_event.get('market_outcomes', ''), str) else pm_event.get('market_outcomes', [])
            outcome1 = str(outcomes[0]).strip().lower()
            outcome2 = str(outcomes[1]).strip().lower()
            # If outcomes are "Yes"/"No", use homeTeamName/awayTeamName instead (only if they exist)
            if outcome1 in ('yes', 'no') or outcome2 in ('yes', 'no'):
                pm_home = normalize_team_name(pm_event.get('homeTeamName', ''))
                pm_away = normalize_team_name(pm_event.get('awayTeamName', ''))
                # If homeTeamName/awayTeamName are empty, we can't match - return 0 score
                if not pm_home or not pm_away:
                    return 0.0
            else:
                pm_home = normalize_team_name(outcomes[0])
                pm_away = normalize_team_name(outcomes[1])
        except (json.JSONDecodeError, TypeError, IndexError):
            pm_home = normalize_team_name(pm_event.get('homeTeamName', ''))
            pm_away = normalize_team_name(pm_event.get('awayTeamName', ''))
            # If homeTeamName/awayTeamName are empty, we can't match - return 0 score
            if not pm_home or not pm_away:
                return 0.0
        
    odds_home = normalize_team_name(odds_event.get('home_team', ''))
    odds_away = normalize_team_name(odds_event.get('away_team', ''))
    
    # Check if this is an NBA event
    is_nba = False
    pm_series_ticker = str(pm_event.get('series_ticker', '')).lower()
    odds_sport_key = str(odds_event.get('sport_key', '')).lower()
    if 'nba' in pm_series_ticker or 'basketball_nba' or 'nhl' in pm_series_ticker or 'icehockey_nhl' in odds_sport_key:
        is_nba = True
    
    # Check for exact matches first
    exact_match1 = (pm_home == odds_home and pm_away == odds_away)
    exact_match2 = (pm_home == odds_away and pm_away == odds_home)
    
    # For NBA events, also check if Polymarket team name is a subset of Odds API name
    # (e.g., "lakers" should match "los angeles lakers")
    if is_nba and not (exact_match1 or exact_match2):
        subset_match1 = (pm_home in odds_home and pm_away in odds_away)
        subset_match2 = (pm_home in odds_away and pm_away in odds_home)
        if subset_match1 or subset_match2:
            exact_match1 = True  # Treat as exact match
    
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

