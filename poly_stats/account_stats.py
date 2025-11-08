import pandas as pd
from py_clob_client.headers.headers import create_level_2_headers
from py_clob_client.clob_types import RequestArgs

from poly_utils.google_utils import get_spreadsheet
from gspread_dataframe import set_with_dataframe
import requests
import json
import os

from dotenv import load_dotenv
load_dotenv()

spreadsheet = get_spreadsheet()

def get_markets_df(wk_full):
    markets_df = pd.DataFrame(wk_full.get_all_records())
    markets_df = markets_df[['question', 'answer1', 'answer2', 'token1', 'token2']]
    markets_df['token1'] = markets_df['token1'].astype(str)
    markets_df['token2'] = markets_df['token2'].astype(str)
    return markets_df

def get_all_orders(client):
    orders = client.client.get_orders()
    orders_df = pd.DataFrame(orders)

    if len(orders_df) > 0:
        orders_df['order_size'] = orders_df['original_size'].astype('float') - orders_df['size_matched'].astype('float')
        orders_df = orders_df[['asset_id', 'order_size', 'side', 'price']]

        orders_df = orders_df.rename(columns={'side': 'order_side', 'price': 'order_price'})
        return orders_df
    else:
        return pd.DataFrame()
    
def get_all_positions(client):
    try:
        positions = client.get_all_positions()
        positions = positions[['asset', 'size', 'avgPrice', 'curPrice', 'percentPnl']]
        positions = positions.rename(columns={'size': 'position_size'})
        return positions
    except:
        return pd.DataFrame()
    
def combine_dfs(orders_df, positions, markets_df, selected_df):
    merged_df = orders_df.merge(positions, left_on=['asset_id'], right_on=['asset'], how='outer')
    merged_df['asset_id'] = merged_df['asset_id'].combine_first(merged_df['asset'])
    merged_df = merged_df.drop(columns='asset', axis=1)

    merge_token1 = merged_df.merge(markets_df, left_on='asset_id', right_on='token1', how='inner')
    merge_token1['merged_with'] = 'token1'

    # Merge with token2
    merge_token2 = merged_df.merge(markets_df, left_on='asset_id', right_on='token2', how='inner')
    merge_token2['merged_with'] = 'token2'

    # Combine the results
    combined_df = pd.concat([merge_token1, merge_token2])

    assert len(merged_df) == len(combined_df)

    combined_df['answer'] = combined_df.apply(
        lambda row: row['answer1'] if row['merged_with'] == 'token1' else row['answer2'], axis=1
    )

    combined_df = combined_df[['question', 'answer', 'order_size', 'order_side', 'order_price', 'position_size', 'avgPrice', 'curPrice']]
    combined_df['order_side'] = combined_df['order_side'].fillna('')
    combined_df = combined_df.fillna(0)

    combined_df['marketInSelected'] = combined_df['question'].isin(selected_df['question'])
    combined_df = combined_df.sort_values('question')
    combined_df = combined_df.sort_values('marketInSelected')
    return combined_df

def get_earnings(client):
    args = RequestArgs(method='GET', request_path='/rewards/user/markets')
    l2Headers = create_level_2_headers(client.signer, client.creds, args)
    url = "https://polymarket.com/api/rewards/markets"

    cursor = ''
    markets = []

    params = {
        "l2Headers": json.dumps(l2Headers),
        "orderBy": "earnings",
        "position": "DESC",
        "makerAddress": os.getenv('BROWSER_WALLET'),
        "authenticationType": "eoa",
        "nextCursor": cursor,
        "requestPath": "/rewards/user/markets"
    }

    r = requests.get(url,  params=params)
    results = r.json()

    data = pd.DataFrame(results['data'])
    data['earnings'] = data['earnings'].apply(lambda x: x[0]['earnings'])

    data = data[data['earnings'] > 0].reset_index(drop=True)
    data = data[['question', 'earnings', 'earning_percentage']]
    return data



def update_stats_once(client):
    spreadsheet = get_spreadsheet()
    wk_full = spreadsheet.worksheet('Full Markets')
    wk_summary = spreadsheet.worksheet('Summary')


    wk_sel = spreadsheet.worksheet('Selected Markets')
    selected_df = pd.DataFrame(wk_sel.get_all_records())
    
    markets_df = get_markets_df(wk_full)
    print("Got spreadsheet...")

    orders_df = get_all_orders(client)
    print("Got Orders...")
    positions = get_all_positions(client)
    print("Got Positions...")

    if len(positions) > 0 or len(orders_df) > 0:
        combined_df = combine_dfs(orders_df, positions, markets_df, selected_df)
        earnings = get_earnings(client.client)
        print("Got Earnings...")
        combined_df = combined_df.merge(earnings, on='question', how='left')

        combined_df = combined_df.fillna(0)
        combined_df = combined_df.round(2)

        combined_df = combined_df.sort_values('earnings', ascending=False)
        combined_df = combined_df[['question', 'answer', 'order_size', 'position_size', 'marketInSelected', 'earnings', 'earning_percentage']]
        wk_summary.clear()

        set_with_dataframe(wk_summary, combined_df, include_index=False, include_column_header=True, resize=True)
    else:
        print("Position or order is empty")