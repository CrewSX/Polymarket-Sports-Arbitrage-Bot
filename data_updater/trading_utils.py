from py_clob_client.constants import POLYGON
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, BalanceAllowanceParams, AssetType
from py_clob_client.order_builder.constants import BUY

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

import json

from dotenv import load_dotenv
load_dotenv()

import time

import os

MAX_INT = 2**256 - 1

def get_clob_client():
    host = "https://clob.polymarket.com"
    key = os.getenv("PK")
    chain_id = POLYGON
    
    if key is None:
        print("Environment variable 'PK' cannot be found")
        return None


    try:
        client = ClobClient(host, key=key, chain_id=chain_id)
        print("Client created", client)
        api_creds = client.create_or_derive_api_creds()
        print("API creds created", api_creds)
        client.set_api_creds(api_creds)
        print("API creds set", client.creds)
        return client
    except Exception as ex: 
        print("Error creating clob client")
        print("________________")
        print(ex)
        return None


def approveContracts():
    web3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com"))
    web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    wallet = web3.eth.account.from_key(os.getenv("PK"))
    
    
    with open('erc20ABI.json', 'r') as file:
        erc20_abi = json.load(file)

    ctf_address = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
    erc1155_set_approval = """[{"inputs": [{ "internalType": "address", "name": "operator", "type": "address" },{ "internalType": "bool", "name": "approved", "type": "bool" }],"name": "setApprovalForAll","outputs": [],"stateMutability": "nonpayable","type": "function"}]"""

    usdc_contract = web3.eth.contract(address="0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", abi=erc20_abi)   # usdc.e
    ctf_contract = web3.eth.contract(address=ctf_address, abi=erc1155_set_approval)
    

    for address in ['0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E', '0xC5d563A36AE78145C45a50134d48A1215220f80a', '0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296']:
        usdc_nonce = web3.eth.get_transaction_count( wallet.address )
        raw_usdc_txn = usdc_contract.functions.approve(address, int(MAX_INT, 0)).build_transaction({
            "chainId": 137, 
            "from": wallet.address, 
            "nonce": usdc_nonce
        })
        signed_usdc_txn = web3.eth.account.sign_transaction(raw_usdc_txn, private_key=os.getenv("PK"))
        usdc_tx_receipt = web3.eth.wait_for_transaction_receipt(signed_usdc_txn, 600)


        print(f'USDC Transaction for {address} returned {usdc_tx_receipt}')
        time.sleep(1)

        ctf_nonce = web3.eth.get_transaction_count( wallet.address )
        
        raw_ctf_approval_txn = ctf_contract.functions.setApprovalForAll(address, True).build_transaction({
            "chainId": 137, 
            "from": wallet.address, 
            "nonce": ctf_nonce
        })

        signed_ctf_approval_tx = web3.eth.account.sign_transaction(raw_ctf_approval_txn, private_key=os.getenv("PK"))
        send_ctf_approval_tx = web3.eth.send_raw_transaction(signed_ctf_approval_tx.raw_transaction)
        ctf_approval_tx_receipt = web3.eth.wait_for_transaction_receipt(send_ctf_approval_tx, 600)

        print(f'CTF Transaction for {address} returned {ctf_approval_tx_receipt}')
        time.sleep(1)



    nonce = web3.eth.get_transaction_count( wallet.address )
    raw_txn_2 = usdc_contract.functions.approve("0xC5d563A36AE78145C45a50134d48A1215220f80a", int(MAX_INT, 0)).build_transaction({
        "chainId": 137, 
        "from": wallet.address, 
        "nonce": nonce
    })
    signed_txn_2 = web3.eth.account.sign_transaction(raw_txn_2, private_key=os.getenv("PK"))
    send_txn_2 = web3.eth.send_raw_transaction(signed_txn_2.raw_transaction)


    nonce = web3.eth.get_transaction_count( wallet.address )
    raw_txn_3 = usdc_contract.functions.approve("0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296", int(MAX_INT, 0)).build_transaction({
        "chainId": 137, 
        "from": wallet.address, 
        "nonce": nonce
    })
    signed_txn_3 = web3.eth.account.sign_transaction(raw_txn_3, private_key=os.getenv("PK"))
    send_txn_3 = web3.eth.send_raw_transaction(signed_txn_3.raw_transaction)
    
    
def market_action( marketId, action, price, size ):
    order_args = OrderArgs(
        price=price,
        size=size,
        side=action,
        token_id=marketId,
    )
    signed_order = get_clob_client().create_order(order_args)
    
    try:
        resp = get_clob_client().post_order(signed_order)
        print(resp)
    except Exception as ex:
        print(ex)
        pass
    
    
def get_position(marketId):
    client = get_clob_client()
    position_res = client.get_balance_allowance(
        BalanceAllowanceParams(
            asset_type=AssetType.CONDITIONAL,
            token_id=marketId
        )
    )
    orderBook = client.get_order_book(marketId)
    price = float(orderBook.bids[-1].price)
    shares = int(position_res['balance']) / 1e6
    return shares * price