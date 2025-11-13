# Arbitrage Calculation Documentation

## Overview

This document explains the arbitrage calculation logic implemented in `arbitrage_calculation.py`. The system identifies profitable opportunities by comparing Polymarket prices with sportsbook odds, detecting directional opportunities (price movement trading).

**Note:** Traditional arbitrage (guaranteed profit) is not applicable here because Polymarket prices always sum to 1.0, representing complete probability coverage. The system focuses on directional opportunities where Polymarket undervalues outcomes compared to sportsbooks.

## Table of Contents

1. [Outcome Matching](#outcome-matching)
2. [Market Type Detection](#market-type-detection)
3. [Directional Opportunities](#directional-opportunities)
4. [Sell Point Recommendations](#sell-point-recommendations)
5. [Usage Examples](#usage-examples)
6. [Configuration Options](#configuration-options)

---

## Outcome Matching

### Purpose

Matches Polymarket outcome names to sportsbook outcome names, handling variations in naming conventions (e.g., "Texas State" vs "Texas State Bobcats").

### Algorithm

The matching uses the same logic as `event_matching.py`:

1. **Normalization**: Both names are normalized using `normalize_team_name()`:
   - Convert to lowercase
   - Strip whitespace
   - Handle None/empty values

2. **Exact Match**: If normalized names are identical, confidence = 1.0

3. **Partial Match**: If one normalized name contains the other, confidence = 0.9
   - Example: "texas state" is contained in "texas state bobcats"

4. **Fuzzy Match**: Uses `fuzz.ratio()` from `rapidfuzz` library:
   - Score = `fuzz.ratio(normalized_pm, normalized_sb) / 100.0`
   - Penalties applied:
     - If score < 0.8: multiply by 0.6 (reduce by 40%)
     - If score < 0.95: multiply by 0.85 (reduce by 15%)

5. **Threshold**: Only matches with confidence >= 0.4 are included

### Example

```python
pm_outcomes = ["Texas State", "Louisiana"]
sb_outcomes = [
    {"name": "Texas State Bobcats", "avg_implied_probability": 0.4},
    {"name": "Louisiana Ragin Cajuns", "avg_implied_probability": 0.6}
]

# Result:
# "Texas State" → "Texas State Bobcats" (confidence: 0.9, partial match)
# "Louisiana" → "Louisiana Ragin Cajuns" (confidence: 0.9, partial match)
```

---

## Market Type Detection

### Purpose

Identifies whether a market is 2-way (two outcomes) or 3-way (three outcomes, typically including a draw).

### Algorithm

Simply counts the number of outcomes:
- 2 outcomes → "2-way"
- 3 outcomes → "3-way"
- Other counts → defaults to "2-way"

### Example

```python
outcomes = ["Team A", "Team B", "Draw"]
market_type = detect_market_type(outcomes)  # Returns "3-way"
```

---

## Why No Traditional Arbitrage?

**Polymarket prices always sum to 1.0** because they represent probabilities in a prediction market. This means:
- All possible outcomes are covered
- No guaranteed arbitrage exists on Polymarket alone
- Traditional arbitrage (betting on all outcomes for guaranteed profit) is not possible

The system focuses on **directional opportunities** instead, where price movements during the game can be exploited.

---

## Directional Opportunities

### Concept

Directional opportunities identify when Polymarket undervalues an outcome compared to sportsbooks. If the outcome performs well during the game, the Polymarket price should rise toward the sportsbook's implied probability, allowing you to sell at a profit.

### Key Insight

Polymarket prices are **dynamic** like stocks - they change throughout the game based on:
- Game events (scores, injuries, momentum)
- Market sentiment (buyers and sellers)
- Information flow

Unlike traditional betting where you must wait for the game to end, you can **sell your position at any time** on Polymarket.

### Mathematical Formula

**Opportunity exists if:** `pm_price < sb_implied_prob`

**Expected Price Movement:** `expected_movement = sb_implied_prob - pm_price`

**Potential Profit Percentage:** `potential_profit = (sb_implied_prob - pm_price) / pm_price`

### Example Calculation

- Polymarket price: 0.40 (40% chance)
- Sportsbook implied prob: 0.50 (50% chance)
- Expected movement: 0.50 - 0.40 = 0.10 (10 percentage points)
- Potential profit: (0.50 - 0.40) / 0.40 = 0.25 = **25%**

**Scenario:**
1. Buy at 0.40 (cost: $40 for 100 shares)
2. If team performs well, price rises toward 0.50
3. Sell at 0.50 (receive: $50)
4. Profit: $10 (25% return)

### When to Use

Directional opportunities are best when:
- You believe the sportsbook's assessment is more accurate
- The game is still in progress (prices can change)
- You're willing to monitor and sell at the right time
- The price difference is significant (>5%)


## Sell Point Recommendations

### Purpose

For directional opportunities, recommends multiple exit points to lock in profits at different risk/reward levels.

### Strategy

Since Polymarket prices are dynamic, we recommend **multiple sell points**:

1. **Fair Value (High Confidence)**: Sell when price reaches sportsbook implied probability
   - Conservative approach
   - Locks in the expected profit
   - High confidence because it's based on sportsbook consensus

2. **Profit Thresholds (Medium Confidence)**: Sell at fixed profit percentages
   - Default: 5%, 10%, 20%
   - Aggressive approach
   - Takes profit early, may miss larger gains
   - Medium confidence because prices may continue rising

### Mathematical Formula

**Fair Value Sell Point:**
- Target price: `sb_implied_prob`
- Profit: `(sb_implied_prob - buy_price) / buy_price`

**Profit Threshold Sell Points:**
- Target price: `buy_price × (1 + profit_target)`
- Profit: `profit_target`

### Example Calculation

**Buy at:** 0.40
**Sportsbook implied prob:** 0.50
**Target profits:** [0.05, 0.10, 0.20]

**Sell Points:**
1. **Fair Value**: 
   - Target: 0.50
   - Profit: (0.50 - 0.40) / 0.40 = 25%
   - Confidence: High

2. **5% Profit**:
   - Target: 0.40 × 1.05 = 0.42
   - Profit: 5%
   - Confidence: Medium

3. **10% Profit**:
   - Target: 0.40 × 1.10 = 0.44
   - Profit: 10%
   - Confidence: Medium

4. **20% Profit**:
   - Target: 0.40 × 1.20 = 0.48
   - Profit: 20%
   - Confidence: Medium

### Trading Strategy

**Conservative Approach:**
- Set sell order at fair value (0.50)
- Wait for price to reach target
- Lock in 25% profit

**Aggressive Approach:**
- Set multiple sell orders at 5%, 10%, 20%
- Take partial profits as price rises
- May capture more profit if price exceeds fair value

**Balanced Approach:**
- Sell 50% at 10% profit
- Sell 50% at fair value
- Diversifies risk and reward

---

## Usage Examples

### Basic Usage

```python
from arbitrage_calculation import detect_arbitrage_opportunities
import json

# Load comparison data
with open('data/arbitrage_comparison_test.json', 'r') as f:
    comparison_data = json.load(f)

# Detect opportunities
opportunities = detect_arbitrage_opportunities(
    comparison_data,
    min_profit_threshold=0.02,  # 2% minimum
    pm_fee=0.0,
    sb_fee=0.0
)

# Process results
for opp in opportunities:
    print(f"Type: {opp['opportunity_type']}")
    print(f"Profit: {opp['profit_margin'] * 100:.2f}%")
    print(f"Market: {opp['market_type']}")
    
    if opp['opportunity_type'] == 'traditional_arbitrage':
        print("Recommended stakes:")
        for stake_info in opp['recommended_stakes']['stakes_by_outcome']:
            print(f"  {stake_info['outcome']}: ${stake_info['stake']:.2f}")
    
    if opp['opportunity_type'] == 'directional':
        print("Sell points:")
        for sell_point in opp['sell_points']:
            print(f"  {sell_point['description']}: {sell_point['target_price']:.3f} "
                  f"({sell_point['profit_percentage'] * 100:.1f}% profit)")
```

### Filtering Opportunities

```python
# Only high-profit opportunities (>5%)
high_profit = [opp for opp in opportunities 
               if opp['profit_margin'] > 0.05]

# Sort by profit margin
sorted_opps = sorted(opportunities, 
                    key=lambda x: x['profit_margin'], 
                    reverse=True)
```

### Individual Function Usage

```python
from arbitrage_calculation import (
    match_pm_to_sb_outcomes,
    calculate_directional_opportunity,
    calculate_sell_points
)

# Match outcomes
pm_outcomes = ["Texas State", "Louisiana"]
sb_outcomes = [
    {"name": "Texas State Bobcats", "avg_implied_probability": 0.4},
    {"name": "Louisiana Ragin Cajuns", "avg_implied_probability": 0.6}
]
matches = match_pm_to_sb_outcomes(pm_outcomes, sb_outcomes)

# Calculate directional opportunity
directional = calculate_directional_opportunity(
    pm_price=0.40,
    sb_implied_prob=0.50,
    pm_outcome_name="Team A"
)

# Calculate sell points
sell_points = calculate_sell_points(
    buy_price=0.40,
    sb_implied_prob=0.50,
    target_profits=[0.05, 0.10, 0.20]
)
```

---

## Configuration Options

### Main Function Parameters

**`detect_arbitrage_opportunities()`**

- `comparison_data` (required): List of comparison dictionaries from `arbitrage_comparison_test.json`
- `min_profit_threshold` (default: 0.02): Minimum profit margin to consider (2%)
- `pm_fee` (default: 0.0): Polymarket transaction fee (currently 0%)
- `sb_fee` (default: 0.0): Sportsbook fee (currently 0%)

### Individual Function Parameters

**`calculate_directional_opportunity()`**
- `min_profit_threshold` (default: 0.05): Minimum expected profit (5%)

**`calculate_sell_points()`**
- `target_profits` (default: [0.05, 0.10, 0.20]): List of profit percentages for sell points

### Recommended Settings

**Conservative (Lower Risk):**
```python
opportunities = detect_arbitrage_opportunities(
    comparison_data,
    min_profit_threshold=0.05,  # 5% minimum
    pm_fee=0.02,  # 2% Polymarket fee
    sb_fee=0.0
)
```

**Aggressive (Higher Risk, More Opportunities):**
```python
opportunities = detect_arbitrage_opportunities(
    comparison_data,
    min_profit_threshold=0.01,  # 1% minimum
    pm_fee=0.0,
    sb_fee=0.0
)
```

**Balanced (Default):**
```python
opportunities = detect_arbitrage_opportunities(
    comparison_data,
    min_profit_threshold=0.02,  # 2% minimum
    pm_fee=0.0,
    sb_fee=0.0
)
```

---

## Important Notes

### Polymarket vs Traditional Betting

1. **Dynamic Pricing**: Polymarket prices change during the game, unlike fixed sportsbook odds
2. **Early Exit**: You can sell your position at any time, not just at game end
3. **Market Depth**: Consider `pm_liquidity` and `pm_spread` when evaluating opportunities
4. **Price Movement**: Prices move based on game events, so directional opportunities require monitoring

### Risk Considerations

1. **Directional Opportunities**: Higher risk, requires price movement in your favor
2. **Liquidity**: Low liquidity markets may have wider spreads, reducing profit
3. **Timing**: Prices can move against you before you can execute trades
4. **Market Efficiency**: Polymarket prices may be correct, and sportsbook odds may be wrong

### Best Practices

1. **Verify Matches**: Always check that outcome matching is correct
2. **Check Liquidity**: Ensure sufficient liquidity for your stake size
3. **Monitor Spreads**: Wide spreads reduce effective profit
4. **Set Limits**: Use sell points to lock in profits
5. **Diversify**: Don't put all capital in one opportunity

---

## Mathematical Proofs

### Directional Opportunity Profit

**Given:**
- Buy price: `P_buy`
- Target price: `P_target`
- Stake: `S`

**Cost:** `S × P_buy`
**Return:** `S × P_target`
**Profit:** `S × (P_target - P_buy)`
**Profit Percentage:** `(P_target - P_buy) / P_buy`

**If P_target = sb_implied_prob and P_buy < sb_implied_prob:**
- Profit percentage = `(sb_implied_prob - P_buy) / P_buy > 0`

---

## Conclusion

The arbitrage calculation system provides a comprehensive framework for identifying profitable opportunities by comparing Polymarket and sportsbook prices. It handles both guaranteed arbitrage (traditional) and speculative opportunities (directional), with detailed stake recommendations and sell point guidance.

For questions or issues, refer to the test suite in `tests/test_arbitrage_calculation.py` for usage examples.

