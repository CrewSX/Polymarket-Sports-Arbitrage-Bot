"""Tests for odds format conversion utilities."""
import pytest
from poly_sports.utils.odds_utils import (
    american_to_decimal,
    decimal_to_american,
    american_to_implied_prob,
    decimal_to_implied_prob,
    implied_prob_to_american,
    implied_prob_to_decimal,
)


class TestAmericanToDecimal:
    """Test conversion from American odds to decimal odds."""
    
    def test_positive_american_to_decimal(self):
        """Test positive American odds conversion."""
        # +100 = 2.0 decimal
        assert american_to_decimal(100) == pytest.approx(2.0, rel=1e-6)
        # +200 = 3.0 decimal
        assert american_to_decimal(200) == pytest.approx(3.0, rel=1e-6)
        # +150 = 2.5 decimal
        assert american_to_decimal(150) == pytest.approx(2.5, rel=1e-6)
    
    def test_negative_american_to_decimal(self):
        """Test negative American odds conversion."""
        # -100 = 2.0 decimal
        assert american_to_decimal(-100) == pytest.approx(2.0, rel=1e-6)
        # -200 = 1.5 decimal
        assert american_to_decimal(-200) == pytest.approx(1.5, rel=1e-6)
        # -150 = 1.666... decimal
        assert american_to_decimal(-150) == pytest.approx(1.6666667, rel=1e-6)
    
    def test_even_money_american_to_decimal(self):
        """Test even money odds (100/-100)."""
        assert american_to_decimal(100) == pytest.approx(2.0, rel=1e-6)
        assert american_to_decimal(-100) == pytest.approx(2.0, rel=1e-6)


class TestDecimalToAmerican:
    """Test conversion from decimal odds to American odds."""
    
    def test_decimal_to_positive_american(self):
        """Test decimal odds > 2.0 convert to positive American."""
        # 2.0 = +100
        assert decimal_to_american(2.0) == 100
        # 3.0 = +200
        assert decimal_to_american(3.0) == 200
        # 2.5 = +150
        assert decimal_to_american(2.5) == 150
    
    def test_decimal_to_negative_american(self):
        """Test decimal odds < 2.0 convert to negative American."""
        # 1.5 = -200
        assert decimal_to_american(1.5) == -200
        # 1.666... = -150
        assert decimal_to_american(1.6666667) == -150
        # 1.1 = -1000
        assert decimal_to_american(1.1) == -1000
    
    def test_even_money_decimal_to_american(self):
        """Test even money decimal odds."""
        # 2.0 can be +100 or -100, function should return +100
        assert decimal_to_american(2.0) == 100


class TestAmericanToImpliedProb:
    """Test conversion from American odds to implied probability."""
    
    def test_positive_american_to_implied_prob(self):
        """Test positive American odds to probability."""
        # +100 = 0.5 probability
        assert american_to_implied_prob(100) == pytest.approx(0.5, rel=1e-6)
        # +200 = 0.333... probability
        assert american_to_implied_prob(200) == pytest.approx(0.3333333, rel=1e-6)
        # +150 = 0.4 probability
        assert american_to_implied_prob(150) == pytest.approx(0.4, rel=1e-6)
    
    def test_negative_american_to_implied_prob(self):
        """Test negative American odds to probability."""
        # -100 = 0.5 probability
        assert american_to_implied_prob(-100) == pytest.approx(0.5, rel=1e-6)
        # -200 = 0.666... probability
        assert american_to_implied_prob(-200) == pytest.approx(0.6666667, rel=1e-6)
        # -150 = 0.6 probability
        assert american_to_implied_prob(-150) == pytest.approx(0.6, rel=1e-6)


class TestDecimalToImpliedProb:
    """Test conversion from decimal odds to implied probability."""
    
    def test_decimal_to_implied_prob(self):
        """Test decimal odds to probability conversion."""
        # 2.0 = 0.5 probability
        assert decimal_to_implied_prob(2.0) == pytest.approx(0.5, rel=1e-6)
        # 3.0 = 0.333... probability
        assert decimal_to_implied_prob(3.0) == pytest.approx(0.3333333, rel=1e-6)
        # 1.5 = 0.666... probability
        assert decimal_to_implied_prob(1.5) == pytest.approx(0.6666667, rel=1e-6)
        # 1.25 = 0.8 probability
        assert decimal_to_implied_prob(1.25) == pytest.approx(0.8, rel=1e-6)


class TestImpliedProbToAmerican:
    """Test conversion from implied probability to American odds."""
    
    def test_implied_prob_to_positive_american(self):
        """Test probability < 0.5 converts to positive American."""
        # 0.4 = +150
        assert implied_prob_to_american(0.4) == 150
        # 0.333... = +200
        assert implied_prob_to_american(0.3333333) == 200
        # 0.25 = +300
        assert implied_prob_to_american(0.25) == 300
    
    def test_implied_prob_to_negative_american(self):
        """Test probability > 0.5 converts to negative American."""
        # 0.6 = -150
        assert implied_prob_to_american(0.6) == -150
        # 0.666... = -200
        assert implied_prob_to_american(0.6666667) == -200
        # 0.8 = -400
        assert implied_prob_to_american(0.8) == -400
    
    def test_even_money_implied_prob_to_american(self):
        """Test 0.5 probability converts to +100."""
        assert implied_prob_to_american(0.5) == 100
    
    def test_edge_cases(self):
        """Test very small and large probabilities."""
        # Very small probability
        assert implied_prob_to_american(0.01) > 0  # Should be positive
        # Very large probability
        assert implied_prob_to_american(0.99) < 0  # Should be negative


class TestImpliedProbToDecimal:
    """Test conversion from implied probability to decimal odds."""
    
    def test_implied_prob_to_decimal(self):
        """Test probability to decimal odds conversion."""
        # 0.5 = 2.0 decimal
        assert implied_prob_to_decimal(0.5) == pytest.approx(2.0, rel=1e-6)
        # 0.333... = 3.0 decimal
        assert implied_prob_to_decimal(0.3333333) == pytest.approx(3.0, rel=1e-6)
        # 0.666... = 1.5 decimal
        assert implied_prob_to_decimal(0.6666667) == pytest.approx(1.5, rel=1e-6)
        # 0.8 = 1.25 decimal
        assert implied_prob_to_decimal(0.8) == pytest.approx(1.25, rel=1e-6)
    
    def test_edge_cases(self):
        """Test edge case probabilities."""
        # Very small probability
        result = implied_prob_to_decimal(0.01)
        assert result > 1.0
        assert result <= 100.0  # 1/0.01 = 100.0 exactly
        # Very large probability
        result = implied_prob_to_decimal(0.99)
        assert result > 1.0
        assert result < 2.0


class TestRoundTripConversions:
    """Test that conversions are reversible."""
    
    def test_american_decimal_round_trip(self):
        """Test American -> Decimal -> American conversion."""
        test_cases = [100, -100, 200, -200, 150, -150, 300, -300]
        for american in test_cases:
            decimal = american_to_decimal(american)
            converted_back = decimal_to_american(decimal)
            # Allow small rounding differences
            # Note: +100 and -100 both convert to 2.0, so round trip isn't perfect for even money
            if american in [100, -100]:
                assert converted_back in [100, -100]  # Either is acceptable
            else:
                assert abs(converted_back - american) <= 1
    
    def test_american_prob_round_trip(self):
        """Test American -> Probability -> American conversion."""
        test_cases = [100, -100, 200, -200, 150, -150]
        for american in test_cases:
            prob = american_to_implied_prob(american)
            converted_back = implied_prob_to_american(prob)
            # Allow small rounding differences
            # Note: +100 and -100 both convert to 0.5 prob, so round trip isn't perfect for even money
            if american in [100, -100]:
                assert converted_back == 100  # Should return +100 for 0.5 prob
            else:
                assert abs(converted_back - american) <= 1
    
    def test_decimal_prob_round_trip(self):
        """Test Decimal -> Probability -> Decimal conversion."""
        test_cases = [1.5, 2.0, 2.5, 3.0, 1.25, 1.1]
        for decimal in test_cases:
            prob = decimal_to_implied_prob(decimal)
            converted_back = implied_prob_to_decimal(prob)
            assert converted_back == pytest.approx(decimal, rel=1e-5)

