# Poly-Merger

A utility for merging Polymarket positions efficiently. This tool helps in consolidating opposite positions in the same market, allowing you to:

1. Reduce gas costs
2. Free up capital
3. Simplify position management

## How It Works

The merger tool interacts with Polymarket's smart contracts to combine opposite positions in binary markets. When you hold both YES and NO shares in the same market, this tool will merge them to recover your USDC.

## Usage

The merger is invoked through the main Poly-Maker bot when position merging conditions are met, but you can also use it independently:

```
node merge.js [amount_to_merge] [condition_id] [is_neg_risk_market]
```

Example:
```
node merge.js 1000000 0xasdasda true
```

This would merge 1 USDC worth of opposing positions in market 0xasdasda, which is a negative risk market. 0xasdasda should be condition_id

## Prerequisites

- Node.js
- ethers.js v5.x
- A .env file with your Polygon network private key

## Notes

This implementation is based on open-source Polymarket code but has been optimized for automated market making operations.