"""Team name extractor registry for sport-specific extraction logic."""
from typing import Dict
from poly_sports.processing.extractors.base import TeamNameExtractor
from poly_sports.processing.extractors.default import DefaultTeamNameExtractor
from poly_sports.processing.extractors.cfb import CFBTeamNameExtractor


# Registry mapping series_ticker patterns to extractor instances
TEAM_NAME_EXTRACTOR_REGISTRY: Dict[str, TeamNameExtractor] = {
    'cfb': CFBTeamNameExtractor(),
    # Default extractor will be used for all other sports
}

# Default extractor instance
_default_extractor = DefaultTeamNameExtractor()


def get_team_name_extractor(series_ticker: str) -> TeamNameExtractor:
    """
    Get the appropriate team name extractor for a given series_ticker.
    
    Args:
        series_ticker: Series ticker from Polymarket event (e.g., 'cfb', 'nfl', 'nba')
        
    Returns:
        TeamNameExtractor instance appropriate for the sport.
        Returns DefaultTeamNameExtractor if no specific extractor is registered.
    """
    if not series_ticker:
        return _default_extractor
    
    # Normalize series_ticker for lookup
    ticker_lower = str(series_ticker).lower().strip()
    
    # Check for exact match first
    if ticker_lower in TEAM_NAME_EXTRACTOR_REGISTRY:
        return TEAM_NAME_EXTRACTOR_REGISTRY[ticker_lower]
    
    # Check for pattern matches (e.g., 'cfb-2025' should match 'cfb')
    if ticker_lower.startswith('cfb'):
        return TEAM_NAME_EXTRACTOR_REGISTRY.get('cfb', _default_extractor)
    
    # Default to default extractor
    return _default_extractor


__all__ = [
    'TeamNameExtractor',
    'DefaultTeamNameExtractor',
    'CFBTeamNameExtractor',
    'TEAM_NAME_EXTRACTOR_REGISTRY',
    'get_team_name_extractor',
]

