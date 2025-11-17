"""Sport key auto-detection for Polymarket events."""
from typing import Dict, Any, Optional


# Mapping of Polymarket series tickers to The Odds API sport keys
SERIES_TICKER_MAP = {
    'nfl': 'americanfootball_nfl',
    'nba': 'basketball_nba',
    'mlb': 'baseball_mlb',
    'nhl': 'icehockey_nhl',
    'ncaaf': 'americanfootball_ncaaf',
    'ncaab': 'basketball_ncaab',
    'cwbb': 'basketball_ncaab',  # College Women's Basketball
    'cbb': 'basketball_ncaab',   # College Basketball
    'cfb': 'americanfootball_ncaaf',  # College Football
    'ncaa-cbb': 'basketball_ncaab',  # College Basketball (with hyphen)
    'soccer': 'soccer_epl',  # Default to EPL, may need more specific mapping
    'ufc': 'mma_mixed_martial_arts',
    'mma': 'mma_mixed_martial_arts',
    'uef-qualifiers': 'soccer_fifa_world_cup_qualifiers_europe',
    'primera-divisin-argentina': 'soccer_argentina_primera_division',
    'nba-2026': 'basketball_nba',
    'odi': 'cricket_odi',
    'cfb-2025': 'americanfootball_ncaaf',
    'brazil-serie-a': 'soccer_brazil_campeonato'
}

# Known team name patterns for each sport
NFL_TEAMS = [
    'patriots', 'chiefs', 'bills', 'dolphins', 'jets', 'bengals', 'ravens', 'steelers',
    'browns', 'texans', 'colts', 'jaguars', 'titans', 'broncos', 'raiders', 'chargers',
    'cowboys', 'giants', 'eagles', 'commanders', 'packers', 'lions', 'vikings', 'bears',
    'falcons', 'panthers', 'saints', 'buccaneers', 'rams', 'cardinals', '49ers', 'seahawks'
]

NBA_TEAMS = [
    'lakers', 'celtics', 'warriors', 'nets', 'knicks', 'bulls', 'heat', 'mavericks',
    'clippers', 'nuggets', 'rockets', 'suns', 'bucks', '76ers', 'raptors', 'jazz',
    'trail blazers', 'thunder', 'spurs', 'pistons', 'cavaliers', 'pacers', 'hornets',
    'hawks', 'wizards', 'magic', 'kings', 'pelicans', 'grizzlies', 'timberwolves'
]

MLB_TEAMS = [
    'yankees', 'red sox', 'dodgers', 'giants', 'cubs', 'cardinals', 'astros', 'braves',
    'mets', 'phillies', 'angels', 'rangers', 'mariners', 'padres', 'rockies', 'diamondbacks',
    'twins', 'white sox', 'tigers', 'royals', 'indians', 'guardians', 'rays', 'blue jays',
    'orioles', 'athletics', 'marlins', 'nationals', 'brewers', 'pirates', 'reds'
]

NHL_TEAMS = [
    'bruins', 'maple leafs', 'canadiens', 'rangers', 'islanders', 'devils', 'flyers',
    'capitals', 'penguins', 'hurricanes', 'lightning', 'panthers', 'sabres', 'senators',
    'red wings', 'blackhawks', 'wild', 'jets', 'avalanche', 'stars', 'predators',
    'blues', 'coyotes', 'golden knights', 'kings', 'ducks', 'sharks', 'canucks',
    'flames', 'oilers'
]

NCAF_TEAMS = [
    'crimson tide', 'bulldogs', 'tigers', 'buckeyes', 'sooners', 'longhorns', 'trojans',
    'fighting irish', 'seminoles', 'hurricanes', 'badgers', 'spartans', 'wolverines',
    'ducks', 'bruins', 'cardinal', 'wildcats', 'cougars', 'aggies', 'razorbacks'
]

NCAB_TEAMS = [
    'blue devils', 'tar heels', 'wildcats', 'jayhawks', 'spartans', 'badgers', 'hoosiers',
    'buckeyes', 'wolverines', 'cardinal', 'trojans', 'bruins', 'razorbacks', 'gators',
    'crimson tide', 'tigers', 'bulldogs', 'aggies', 'longhorns', 'sooners'
]


def detect_sport_key(event_data: Dict[str, Any]) -> Optional[str]:
    """
    Auto-detect The Odds API sport key from Polymarket event data.
    
    Detection strategy (in order of priority):
    1. Check series_ticker against known mappings
    2. Analyze team names for sport-specific patterns
    3. Check question/description for sport keywords
    
    Args:
        event_data: Polymarket event dictionary with fields like:
                   - series_ticker: Series identifier
                   - homeTeamName: Home team name
                   - awayTeamName: Away team name
                   - question: Market question text
                   
    Returns:
        The Odds API sport key (e.g., 'americanfootball_nfl') or None if not detected
    """
    if not event_data:
        return None
    
    # Priority 1: Check series_ticker
    series_ticker = event_data.get('series_ticker', '')
    if series_ticker:
        ticker_lower = str(series_ticker).lower().strip()
        
        # Check exact match first
        if ticker_lower in SERIES_TICKER_MAP:
            return SERIES_TICKER_MAP[ticker_lower]
        
        # Check for patterns (e.g., "cfb-2025" should match "cfb")
        # College Basketball: ncaa-cbb, ncaa_cbb (check this first to avoid false matches)
        if 'ncaa-cbb' in ticker_lower or 'ncaa_cbb' in ticker_lower:
            return 'basketball_ncaab'
        
        # College Football: cfb, cfb-*, cfb_* (e.g., "cfb-2025")
        if ticker_lower.startswith('cfb'):
            return 'americanfootball_ncaaf'
        
        # College Basketball: cbb-*, cbb_* (but not if it's part of ncaa-cbb, already handled above)
        if ticker_lower.startswith('cbb-') or ticker_lower.startswith('cbb_'):
            return 'basketball_ncaab'
    
    # Priority 2: Analyze team names
    home_team = str(event_data.get('homeTeamName', '')).lower()
    away_team = str(event_data.get('awayTeamName', '')).lower()
    all_teams_text = f"{home_team} {away_team}"
    
    # Check NFL teams
    if any(team in all_teams_text for team in NFL_TEAMS):
        return 'americanfootball_nfl'
    
    # Check NBA teams
    if any(team in all_teams_text for team in NBA_TEAMS):
        return 'basketball_nba'
    
    # Check MLB teams
    if any(team in all_teams_text for team in MLB_TEAMS):
        return 'baseball_mlb'
    
    # Check NHL teams
    if any(team in all_teams_text for team in NHL_TEAMS):
        return 'icehockey_nhl'
    
    # Check NCAAF teams
    if any(team in all_teams_text for team in NCAF_TEAMS):
        return 'americanfootball_ncaaf'
    
    # Check NCAAB teams
    if any(team in all_teams_text for team in NCAB_TEAMS):
        return 'basketball_ncaab'
    
    # Priority 3: Check question/description for keywords
    question = str(event_data.get('question', '')).lower()
    description = str(event_data.get('description', '')).lower()
    all_text = f"{question} {description}"
    
    # Sport keywords
    if any(keyword in all_text for keyword in ['nfl', 'national football league', 'football game']):
        return 'americanfootball_nfl'
    if any(keyword in all_text for keyword in ['nba', 'national basketball association', 'basketball game']):
        return 'basketball_nba'
    if any(keyword in all_text for keyword in ['mlb', 'major league baseball', 'baseball game']):
        return 'baseball_mlb'
    if any(keyword in all_text for keyword in ['nhl', 'national hockey league', 'hockey game']):
        return 'icehockey_nhl'
    if any(keyword in all_text for keyword in ['ncaaf', 'college football', 'cfb']):
        return 'americanfootball_ncaaf'
    if any(keyword in all_text for keyword in ['ncaab', 'college basketball', 'cbb', 'cwbb']):
        return 'basketball_ncaab'
    if any(keyword in all_text for keyword in ['ufc', 'mma', 'mixed martial arts', 'fight']):
        return 'mma_mixed_martial_arts'
    if any(keyword in all_text for keyword in ['soccer', 'premier league', 'mls', 'football match']):
        # Default to EPL, but could be more specific
        return 'soccer_epl'
    
    return None

