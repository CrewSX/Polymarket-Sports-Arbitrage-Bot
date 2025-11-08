/**
 * Poly-Merger: Position Merging Utility for Polymarket
 * 
 * This script handles merging of YES and NO positions in Polymarket prediction markets
 * to recover collateral. It works with both regular and negative risk markets.
 * 
 * The merger supports Gnosis Safe wallets through the safe-helpers.js utility.
 * 
 * Usage:
 *   node merge.js [amountToMerge] [conditionId] [isNegRiskMarket]
 * 
 * Example:
 *   node merge.js 1000000 12345 true
 */

const { ethers } = require('ethers');
const { resolve } = require('path');
const { existsSync } = require('fs');
const { signAndExecuteSafeTransaction } = require('./safe-helpers');
const { safeAbi } = require('./safeAbi');

// Load environment variables
const localEnvPath = resolve(__dirname, '.env');
const parentEnvPath = resolve(__dirname, '../.env');
const envPath = existsSync(localEnvPath) ? localEnvPath : parentEnvPath;
require('dotenv').config({ path: envPath })

// Connect to Polygon network
const provider = new ethers.providers.JsonRpcProvider("https://polygon-rpc.com");
const privateKey = process.env.PK;
const wallet = new ethers.Wallet(privateKey, provider);

// Polymarket contract addresses
const addresses = {
  // Adapter contract for negative risk markets
  neg_risk_adapter: '0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296',
  // USDC token contract on Polygon
  collateral: '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
  // Main conditional tokens contract for prediction markets
  conditional_tokens: '0x4D97DCd97eC945f40cF65F87097ACe5EA0476045'
};

// Minimal ABIs for the contracts we interact with
const negRiskAdapterAbi = [
  "function mergePositions(bytes32 conditionId, uint256 amount)"
];

const conditionalTokensAbi = [
  "function mergePositions(address collateralToken, bytes32 parentCollectionId, bytes32 conditionId, uint256[] partition, uint256 amount)"
];

/**
 * Merges YES and NO positions in a Polymarket prediction market to recover USDC collateral.
 * 
 * This function handles both regular and negative risk markets via different contract calls.
 * It uses the Gnosis Safe wallet infrastructure for secure transaction execution.
 * 
 * @param {string|number} amountToMerge - Raw amount of tokens to merge (typically expressed in raw units, e.g., 1000000 = 1 USDC)
 * @param {string|number} conditionId - The market's condition ID
 * @param {boolean} isNegRiskMarket - Whether this is a negative risk market (uses different contract)
 * @returns {string} The transaction hash of the merge operation
 */
async function mergePositions(amountToMerge, conditionId, isNegRiskMarket) {
    // Log parameters for debugging
    console.log(amountToMerge, conditionId, isNegRiskMarket);
    
    // Prepare transaction parameters
    const nonce = await provider.getTransactionCount(wallet.address);
    const gasPrice = await provider.getGasPrice();
    const gasLimit = 10000000;  // Set high gas limit to ensure transaction completes

    let tx;
    // Different contract calls for different market types
    if (isNegRiskMarket) {
      // For negative risk markets, use the adapter contract
      const negRiskAdapter = new ethers.Contract(addresses.neg_risk_adapter, negRiskAdapterAbi, wallet);
      tx = await negRiskAdapter.populateTransaction.mergePositions(conditionId, amountToMerge);
    } else {
      // For regular markets, use the conditional tokens contract directly
      const conditionalTokens = new ethers.Contract(addresses.conditional_tokens, conditionalTokensAbi, wallet);
      tx = await conditionalTokens.populateTransaction.mergePositions(
        addresses.collateral,        // USDC contract
        ethers.constants.HashZero,   // Parent collection ID (0 for top-level markets)
        conditionId,                 // Market ID
        [1, 2],                      // Partition (indexes of outcomes to merge)
        amountToMerge                // Amount to merge
      );
    }

    // Prepare full transaction object
    const transaction = {
      ...tx,
      chainId: 137,       // Polygon chain ID
      gasPrice: gasPrice,
      gasLimit: gasLimit,
      nonce: nonce
    };

    // Get the Safe address from environment variables
    const safeAddress = process.env.BROWSER_ADDRESS;
    const safe = new ethers.Contract(safeAddress, safeAbi, wallet);

    // Execute the transaction through the Safe
    console.log("Signing Transaction")
    const txResponse = await signAndExecuteSafeTransaction(
      wallet, 
      safe, 
      transaction.to, 
      transaction.data, 
      { 
        gasPrice: transaction.gasPrice, 
        gasLimit: transaction.gasLimit 
      }
    );
    
    console.log("Sent transaction. Waiting for response")
    const txReceipt = await txResponse.wait();
    
    console.log("merge positions " + txReceipt.transactionHash);
    return txReceipt.transactionHash;
}

// Parse command line arguments
const args = process.argv.slice(2);

// Amount of tokens to merge (in raw units, e.g., 1000000 = 1 USDC)
const amountToMerge = args[0]; 

// The market's condition ID
const conditionId = args[1];

// Whether this is a negative risk market (true/false)
const isNegRiskMarket = args[2] === 'true';

// Execute the merge operation and handle any errors
mergePositions(amountToMerge, conditionId, isNegRiskMarket)
  .catch(error => {
    console.error("Error merging positions:", error);
    process.exit(1);
  });