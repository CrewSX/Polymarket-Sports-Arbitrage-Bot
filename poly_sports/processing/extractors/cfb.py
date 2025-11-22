"""CFB-specific team name extractor for Polymarket events."""
from typing import Dict, Any, Tuple
from poly_sports.processing.extractors.base import TeamNameExtractor
from poly_sports.processing.extractors.default import DefaultTeamNameExtractor
from poly_sports.processing.extractors.utils import (
    normalize_team_name,
    extract_school_names_from_outcomes
)


class CFBTeamNameExtractor(TeamNameExtractor):
    """Extractor for college football that uses school names from market_outcomes."""
    
    def __init__(self):
        """Initialize with a default extractor for fallback."""
        self._default_extractor = DefaultTeamNameExtractor()
    
    def extract_team_names(self, pm_event: Dict[str, Any]) -> Tuple[str, str]:
        """
        Extract team names using school names from market_outcomes for CFB.
        
        For college football, market_outcomes contains full school names which are
        more accurate than team names alone. Combines school names with team names
        when appropriate.
        
        Falls back to DefaultTeamNameExtractor if school names are not available.
        
        Args:
            pm_event: Polymarket event dictionary
            
        Returns:
            Tuple of (home_team, away_team) as normalized strings.
            Returns empty strings if extraction fails.
        """
        # Try to get school names from market_outcomes
        school_away, school_home = extract_school_names_from_outcomes(pm_event)
        
        if school_home and school_away:
            # Use school names from market_outcomes for college football
            normalized_school_home = normalize_team_name(school_home)
            normalized_home_team = normalize_team_name(pm_event.get('homeTeamName', ''))
            
            if normalized_school_home and normalized_home_team and normalized_school_home.endswith(normalized_home_team):
                pm_home = normalized_school_home
            else:
                pm_home = normalized_school_home + " " + normalized_home_team

            normalized_school_away = normalize_team_name(school_away)
            normalized_away_team = normalize_team_name(pm_event.get('awayTeamName', ''))
            
            if normalized_school_away and normalized_away_team and normalized_school_away.endswith(normalized_away_team):
                pm_away = normalized_school_away
            else:
                pm_away = normalized_school_away + " " + normalized_away_team
            
            return (pm_home, pm_away)
        
        # Fallback to default extractor if school names not available
        return self._default_extractor.extract_team_names(pm_event)

