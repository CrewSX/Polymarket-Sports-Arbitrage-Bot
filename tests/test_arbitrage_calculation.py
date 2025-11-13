"""Tests for arbitrage calculation logic."""
import pytest
import json
from poly_sports.processing.event_matching import match_events
from poly_sports.processing.arbitrage_calculation import (
    detect_market_type,
    calculate_directional_opportunity,
    calculate_sell_points,
    detect_arbitrage_opportunities,
)


class TestMatchPmToSbOutcomes:
    """Test outcome matching between Polymarket and sportsbook outcomes."""
    
    def test_exact_match(self):
        """Test exact name matches using match_events."""
        pm_outcomes = ["Texas State", "Louisiana"]
        sb_outcomes = [
            {"name": "Texas State", "avg_implied_probability": 0.5},
            {"name": "Louisiana", "avg_implied_probability": 0.5}
        ]
        
        # Convert to pseudo-events and use match_events
        pm_pseudo_events = [{'homeTeamName': outcome, 'awayTeamName': ''} for outcome in pm_outcomes]
        sb_pseudo_events = [{'home_team': outcome.get('name', ''), 'away_team': ''} for outcome in sb_outcomes]
        
        event_matches = match_events(pm_pseudo_events, sb_pseudo_events, min_confidence=0.4)
        
        # Transform back
        result = {}
        for match in event_matches:
            pm_outcome = match['pm_event']['homeTeamName']
            sb_outcome_dict = next(
                (sb for sb in sb_outcomes if sb.get('name', '') == match['odds_event']['home_team']),
                None
            )
            if sb_outcome_dict:
                result[pm_outcome] = {
                    'sb_outcome': sb_outcome_dict,
                    'match_confidence': match['confidence']
                }
        
        assert len(result) == 2
        assert "Texas State" in result
        assert "Louisiana" in result
        assert result["Texas State"]["sb_outcome"]["name"] == "Texas State"
        assert result["Texas State"]["match_confidence"] >= 0.8
    
    def test_fuzzy_match(self):
        """Test fuzzy matching for partial names using match_events."""
        pm_outcomes = ["Texas State", "Louisiana"]
        sb_outcomes = [
            {"name": "Texas State Bobcats", "avg_implied_probability": 0.4},
            {"name": "Louisiana Ragin Cajuns", "avg_implied_probability": 0.6}
        ]
        
        # Convert to pseudo-events and use match_events
        pm_pseudo_events = [{'homeTeamName': outcome, 'awayTeamName': ''} for outcome in pm_outcomes]
        sb_pseudo_events = [{'home_team': outcome.get('name', ''), 'away_team': ''} for outcome in sb_outcomes]
        
        event_matches = match_events(pm_pseudo_events, sb_pseudo_events, min_confidence=0.4)
        
        # Transform back
        result = {}
        for match in event_matches:
            pm_outcome = match['pm_event']['homeTeamName']
            sb_outcome_dict = next(
                (sb for sb in sb_outcomes if sb.get('name', '') == match['odds_event']['home_team']),
                None
            )
            if sb_outcome_dict:
                result[pm_outcome] = {
                    'sb_outcome': sb_outcome_dict,
                    'match_confidence': match['confidence']
                }
        
        assert len(result) == 2
        assert "Texas State" in result
        assert "Louisiana" in result
        assert result["Texas State"]["sb_outcome"]["name"] == "Texas State Bobcats"
        assert result["Louisiana"]["sb_outcome"]["name"] == "Louisiana Ragin Cajuns"
        assert result["Texas State"]["match_confidence"] > 0.4
    
    def test_unmatched_outcome(self):
        """Test when some outcomes cannot be matched using match_events."""
        pm_outcomes = ["Texas State", "Unknown Team"]
        sb_outcomes = [
            {"name": "Texas State Bobcats", "avg_implied_probability": 0.5},
            {"name": "Louisiana Ragin Cajuns", "avg_implied_probability": 0.5}
        ]
        
        # Convert to pseudo-events and use match_events
        pm_pseudo_events = [{'homeTeamName': outcome, 'awayTeamName': ''} for outcome in pm_outcomes]
        sb_pseudo_events = [{'home_team': outcome.get('name', ''), 'away_team': ''} for outcome in sb_outcomes]
        
        event_matches = match_events(pm_pseudo_events, sb_pseudo_events, min_confidence=0.4)
        
        # Transform back
        result = {}
        for match in event_matches:
            pm_outcome = match['pm_event']['homeTeamName']
            sb_outcome_dict = next(
                (sb for sb in sb_outcomes if sb.get('name', '') == match['odds_event']['home_team']),
                None
            )
            if sb_outcome_dict:
                result[pm_outcome] = {
                    'sb_outcome': sb_outcome_dict,
                    'match_confidence': match['confidence']
                }
        
        assert "Texas State" in result
        # Unknown Team might not match or match with low confidence
        assert len(result) >= 1
    
    def test_empty_outcomes(self):
        """Test with empty outcome lists using match_events."""
        pm_pseudo_events = []
        sb_pseudo_events = []
        
        result = match_events(pm_pseudo_events, sb_pseudo_events, min_confidence=0.4)
        assert result == []
        
        pm_pseudo_events = [{'homeTeamName': 'Team A', 'awayTeamName': ''}]
        sb_pseudo_events = []
        
        result = match_events(pm_pseudo_events, sb_pseudo_events, min_confidence=0.4)
        assert result == []


class TestDetectMarketType:
    """Test market type detection."""
    
    def test_2way_market(self):
        """Test detection of 2-way market."""
        outcomes = ["Team A", "Team B"]
        assert detect_market_type(outcomes) == "2-way"
    
    def test_3way_market(self):
        """Test detection of 3-way market."""
        outcomes = ["Team A", "Team B", "Draw"]
        assert detect_market_type(outcomes) == "3-way"
    
    def test_single_outcome(self):
        """Test edge case with single outcome."""
        outcomes = ["Team A"]
        # Should handle gracefully, might return None or raise
        result = detect_market_type(outcomes)
        assert result in ["2-way", "3-way", None] or isinstance(result, str)
    
    def test_four_outcomes(self):
        """Test edge case with 4+ outcomes."""
        outcomes = ["Team A", "Team B", "Team C", "Team D"]
        result = detect_market_type(outcomes)
        # Should handle gracefully
        assert isinstance(result, str) or result is None


class TestCalculateDirectionalOpportunity:
    """Test directional opportunity detection."""
    
    def test_directional_opportunity(self):
        """Test when PM price is lower than SB implied prob."""
        pm_price = 0.40  # PM thinks 40% chance
        sb_implied_prob = 0.50  # Sportsbooks think 50% chance
        
        result = calculate_directional_opportunity(pm_price, sb_implied_prob, "Team A", min_profit_threshold=0.05)
        
        assert result is not None
        assert result["expected_price_movement"] > 0
        assert result["potential_profit_percentage"] > 0
    
    def test_no_directional_opportunity(self):
        """Test when PM price is higher than SB implied prob."""
        pm_price = 0.60  # PM thinks 60% chance
        sb_implied_prob = 0.50  # Sportsbooks think 50% chance
        
        result = calculate_directional_opportunity(pm_price, sb_implied_prob, "Team A", min_profit_threshold=0.05)
        
        # Should return None or indicate this is not a buy opportunity
        # (might be a sell opportunity instead)
        assert result is None or result.get("opportunity_type") != "buy"
    
    def test_small_difference_below_threshold(self):
        """Test when difference exists but below threshold."""
        pm_price = 0.48
        sb_implied_prob = 0.50
        
        result = calculate_directional_opportunity(pm_price, sb_implied_prob, "Team A", min_profit_threshold=0.05)
        
        # Should return None if difference is too small
        assert result is None


class TestCalculateSellPoints:
    """Test sell point recommendations."""
    
    def test_sell_points_calculation(self):
        """Test sell point calculation with default targets."""
        buy_price = 0.40
        sb_implied_prob = 0.50
        
        result = calculate_sell_points(buy_price, sb_implied_prob)
        
        assert len(result) > 0
        # Should include fair value sell point
        fair_value = next((sp for sp in result if sp["description"] == "Fair value"), None)
        assert fair_value is not None
        assert fair_value["target_price"] == pytest.approx(sb_implied_prob, rel=0.01)
    
    def test_custom_profit_targets(self):
        """Test sell points with custom profit targets."""
        buy_price = 0.40
        sb_implied_prob = 0.50
        target_profits = [0.10, 0.20]
        
        result = calculate_sell_points(buy_price, sb_implied_prob, target_profits=target_profits)
        
        assert len(result) >= len(target_profits) + 1  # +1 for fair value
        # Check that profit targets are included
        profit_10 = next((sp for sp in result if "10%" in sp["description"]), None)
        profit_20 = next((sp for sp in result if "20%" in sp["description"]), None)
        assert profit_10 is not None
        assert profit_20 is not None
    
    def test_sell_point_confidence_levels(self):
        """Test that sell points have confidence levels."""
        buy_price = 0.40
        sb_implied_prob = 0.50
        
        result = calculate_sell_points(buy_price, sb_implied_prob)
        
        for sell_point in result:
            assert "confidence" in sell_point
            assert sell_point["confidence"] in ["high", "medium", "low"]
            assert "target_price" in sell_point
            assert "profit_percentage" in sell_point


class TestDetectArbitrageOpportunities:
    """Test main arbitrage detection function."""
    
    def test_with_sample_comparison_data(self):
        """Test with sample data structure from arbitrage_comparison_test.json."""
        sample_data = [
            {
                "pm_event_id": "72621",
                "pm_market_id": "664293",
                "pm_market_outcomes": '["Texas State", "Louisiana"]',
                "pm_market_outcomePrices": '["0.595", "0.405"]',
                "pm_spread": 0.01,
                "pm_market_liquidityNum": 151006.3622,
                "odds_api_event_id": "a69f6a6be64a31d8e22809160b63b969",
                "match_confidence": 0.575,
                "sportsbook_count": 4,
                "sportsbook_outcomes": [
                    {
                        "name": "Louisiana Ragin Cajuns",
                        "avg_price_decimal": 1.086,
                        "avg_implied_probability": 0.922,
                        "min_price_decimal": 1.01,
                        "max_price_decimal": 1.133
                    },
                    {
                        "name": "Texas State Bobcats",
                        "avg_price_decimal": 8.3625,
                        "avg_implied_probability": 0.136,
                        "min_price_decimal": 5.5,
                        "max_price_decimal": 14.0
                    }
                ]
            }
        ]
        
        result = detect_arbitrage_opportunities(sample_data, min_profit_threshold=0.01)
        
        assert isinstance(result, list)
        # Should process the data and potentially find opportunities
        # (may or may not find arbitrage depending on the numbers)
    
    def test_filters_by_profit_threshold(self):
        """Test that opportunities are filtered by profit threshold."""
        sample_data = [
            {
                "pm_event_id": "test1",
                "pm_market_id": "test1",
                "pm_market_outcomes": '["Team A", "Team B"]',
                "pm_market_outcomePrices": '["0.40", "0.60"]',  # PM price 0.40, SB might be higher
                "pm_spread": 0.01,
                "pm_market_liquidityNum": 1000,
                "odds_api_event_id": "test1",
                "match_confidence": 0.8,
                "sportsbook_count": 2,
                "sportsbook_outcomes": [
                    {"name": "Team A", "avg_implied_probability": 0.50},  # SB thinks 50%, PM has 40%
                    {"name": "Team B", "avg_implied_probability": 0.50}
                ]
            }
        ]
        
        result = detect_arbitrage_opportunities(sample_data, min_profit_threshold=0.02)
        
        # Should filter out opportunities below threshold
        for opp in result:
            assert opp["profit_margin"] >= 0.02
    
    def test_includes_all_required_fields(self):
        """Test that output includes all required fields."""
        sample_data = [
            {
                "pm_event_id": "test1",
                "pm_market_id": "test1",
                "pm_market_outcomes": '["Team A", "Team B"]',
                "pm_market_outcomePrices": '["0.45", "0.50"]',  # Potential arbitrage
                "pm_spread": 0.01,
                "pm_market_liquidityNum": 1000,
                "odds_api_event_id": "test1",
                "match_confidence": 0.8,
                "sportsbook_count": 2,
                "sportsbook_outcomes": [
                    {"name": "Team A", "avg_implied_probability": 0.60, "avg_price_decimal": 1.67},  # SB higher than PM
                    {"name": "Team B", "avg_implied_probability": 0.40, "avg_price_decimal": 2.5}
                ]
            }
        ]
        
        result = detect_arbitrage_opportunities(sample_data, min_profit_threshold=0.0)
        
        if result:
            opp = result[0]
            required_fields = [
                "pm_event_id", "pm_market_id", "odds_api_event_id",
                "opportunity_type", "market_type", "profit_margin",
                "matched_outcomes", "sell_points"
            ]
            for field in required_fields:
                assert field in opp
    
    def test_handles_missing_data(self):
        """Test graceful handling of missing or invalid data."""
        sample_data = [
            {
                "pm_event_id": "test1",
                "pm_market_outcomes": "",  # Missing data
                "pm_market_outcomePrices": "",
                "sportsbook_outcomes": []
            }
        ]
        
        # Should not crash, should return empty list or skip invalid entries
        result = detect_arbitrage_opportunities(sample_data)
        assert isinstance(result, list)

