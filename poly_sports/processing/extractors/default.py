"""Default team name extractor for Polymarket events."""
import json
from typing import Dict, Any, Tuple
from poly_sports.processing.extractors.base import TeamNameExtractor
from poly_sports.processing.extractors.utils import normalize_team_name


class DefaultTeamNameExtractor(TeamNameExtractor):
    """Default extractor that uses market_outcomes with fallback to homeTeamName/awayTeamName."""
    
    def extract_team_names(self, pm_event: Dict[str, Any]) -> Tuple[str, str]:
        """
        Extract team names from market_outcomes, with fallback to homeTeamName/awayTeamName.
        
        Handles cases where market_outcomes contains "Yes"/"No" by falling back to
        homeTeamName and awayTeamName fields.
        
        Args:
            pm_event: Polymarket event dictionary
            
        Returns:
            Tuple of (home_team, away_team) as normalized strings.
            Returns empty strings if extraction fails.
        """
        # Try to extract from market_outcomes first
        market_outcomes_str = pm_event.get('market_outcomes', '')
        if market_outcomes_str:
            try:
                if isinstance(market_outcomes_str, str):
                    outcomes = json.loads(market_outcomes_str)
                else:
                    outcomes = market_outcomes_str
                
                if isinstance(outcomes, list) and len(outcomes) >= 2:
                    pm_home = normalize_team_name(outcomes[0])
                    pm_away = normalize_team_name(outcomes[1])
                    
                    # If outcomes are "Yes"/"No", use homeTeamName/awayTeamName instead
                    if not pm_home or not pm_away or pm_home in ('yes', 'no') or pm_away in ('yes', 'no'):
                        pm_home = normalize_team_name(pm_event.get('homeTeamName', ''))
                        pm_away = normalize_team_name(pm_event.get('awayTeamName', ''))
                    
                    return (pm_home, pm_away)
            except (json.JSONDecodeError, KeyError, IndexError):
                pass
        
        # Fallback to homeTeamName/awayTeamName
        pm_home = normalize_team_name(pm_event.get('homeTeamName', ''))
        pm_away = normalize_team_name(pm_event.get('awayTeamName', ''))
        
        return (pm_home, pm_away)

