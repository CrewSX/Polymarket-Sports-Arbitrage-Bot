from poly_data.polymarket_client import PolymarketClient
from poly_stats.account_stats import update_stats_once

import pandas as pd
import time
import traceback

client = PolymarketClient()

if __name__ == '__main__':
    while True:
        try:
            update_stats_once(client)
        except Exception as e:
            traceback.print_exc()

        print("Now sleeping\n")
        time.sleep(60 * 60 * 3) #3 hours