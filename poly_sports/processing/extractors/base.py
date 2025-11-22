"""Abstract base class for team name extractors."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple


class TeamNameExtractor(ABC):
    """Abstract base class for extracting team names from Polymarket events."""
    
    @abstractmethod
    def extract_team_names(self, pm_event: Dict[str, Any]) -> Tuple[str, str]:
        """
        Extract home and away team names from a Polymarket event.
        
        Args:
            pm_event: Polymarket event dictionary
            
        Returns:
            Tuple of (home_team, away_team) as normalized strings.
            Returns empty strings if extraction fails.
        """
        pass

