"""Integration tests for end-to-end flow."""
import pytest
from unittest.mock import patch
import os

from poly_sports.data_fetching.fetch_sports_markets import main

# Minimal Gamma-shaped events so extract_arbitrage_data yields one row per market
def _event(eid: str, market_id: str, question: str = "Will Team A win?"):
    return {
        "id": eid,
        "ended": False,
        "markets": [
            {
                "id": market_id,
                "question": question,
                "active": True,
                "closed": False,
            }
        ],
    }


class TestIntegration:
    """Test end-to-end integration."""

    @patch("poly_sports.data_fetching.fetch_sports_markets.fetch_sports_markets")
    @patch("poly_sports.data_fetching.fetch_sports_markets.enrich_events_with_clob_data")
    @patch("poly_sports.data_fetching.fetch_sports_markets.save_json")
    @patch("poly_sports.data_fetching.fetch_sports_markets.save_to_csv")
    @patch("poly_sports.data_fetching.fetch_sports_markets.require_valid_env_private_key")
    @patch.dict(
        os.environ,
        {
            "GAMMA_API_URL": "https://gamma-api.polymarket.com",
            "ENRICH_WITH_CLOB": "false",
            "PK": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        },
    )
    def test_main_flow_without_clob(
        self, mock_req_pk, mock_save_csv, mock_save_json, mock_enrich, mock_fetch
    ):
        """Test main flow without CLOB enrichment."""
        mock_markets = [
            _event("1", "m1", "Will Team A win?"),
            _event("2", "m2", "Will Player B score?"),
        ]

        mock_fetch.return_value = mock_markets

        main()

        mock_fetch.assert_called_once()
        mock_enrich.assert_not_called()
        assert mock_save_json.call_count == 2
        assert mock_save_csv.call_count == 2

        events_saved = mock_save_json.call_args_list[0][0][0]
        arbitrage_saved = mock_save_json.call_args_list[1][0][0]
        assert len(events_saved) == 2
        assert len(arbitrage_saved) == 2

        assert mock_save_csv.call_args_list[0][0][0] == events_saved
        assert mock_save_csv.call_args_list[1][0][0] == arbitrage_saved

    @patch("poly_sports.data_fetching.fetch_sports_markets.fetch_sports_markets")
    @patch("poly_sports.data_fetching.fetch_sports_markets.enrich_events_with_clob_data")
    @patch("poly_sports.data_fetching.fetch_sports_markets.save_json")
    @patch("poly_sports.data_fetching.fetch_sports_markets.save_to_csv")
    @patch("poly_sports.data_fetching.fetch_sports_markets.require_valid_env_private_key")
    @patch.dict(
        os.environ,
        {
            "GAMMA_API_URL": "https://gamma-api.polymarket.com",
            "ENRICH_WITH_CLOB": "true",
            "CLOB_HOST": "https://clob.polymarket.com",
            "PK": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        },
    )
    def test_main_flow_with_clob(
        self, mock_req_pk, mock_save_csv, mock_save_json, mock_enrich, mock_fetch
    ):
        """Test main flow with CLOB enrichment."""
        raw_events = [_event("1", "m1")]

        def _enrich(host, events):
            out = []
            for ev in events:
                ne = dict(ev)
                ne["markets"] = []
                for m in ev.get("markets", []):
                    nm = dict(m)
                    nm["clob_data"] = {
                        "midpoint": "0.55",
                        "buy_price": "0.56",
                        "sell_price": "0.54",
                    }
                    ne["markets"].append(nm)
                out.append(ne)
            return out

        mock_fetch.return_value = raw_events
        mock_enrich.side_effect = _enrich

        main()

        mock_enrich.assert_called_once()
        assert mock_save_json.call_count == 2
        assert mock_save_csv.call_count == 2

        saved_events = mock_save_json.call_args_list[0][0][0]
        assert "clob_data" in saved_events[0]["markets"][0]

    @patch("poly_sports.data_fetching.fetch_sports_markets.fetch_sports_markets")
    @patch("poly_sports.data_fetching.fetch_sports_markets.save_json")
    @patch("poly_sports.data_fetching.fetch_sports_markets.save_to_csv")
    @patch("poly_sports.data_fetching.fetch_sports_markets.require_valid_env_private_key")
    @patch.dict(
        os.environ,
        {
            "GAMMA_API_URL": "https://gamma-api.polymarket.com",
            "ENRICH_WITH_CLOB": "false",
            "PK": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        },
    )
    def test_main_flow_no_sports_markets(
        self, mock_req_pk, mock_save_csv, mock_save_json, mock_fetch
    ):
        """Test main flow when no sports markets are found."""
        mock_fetch.return_value = []

        main()

        assert mock_save_json.call_count == 2
        assert mock_save_csv.call_count == 2

        assert len(mock_save_json.call_args_list[0][0][0]) == 0
        assert len(mock_save_json.call_args_list[1][0][0]) == 0

    @patch("poly_sports.data_fetching.fetch_sports_markets.fetch_sports_markets")
    @patch("poly_sports.data_fetching.fetch_sports_markets.save_json")
    @patch("poly_sports.data_fetching.fetch_sports_markets.save_to_csv")
    @patch("poly_sports.data_fetching.fetch_sports_markets.require_valid_env_private_key")
    @patch.dict(
        os.environ,
        {
            "GAMMA_API_URL": "https://gamma-api.polymarket.com",
            "ENRICH_WITH_CLOB": "false",
            "OUTPUT_DIR": "/tmp/test_output",
            "PK": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        },
    )
    def test_main_flow_custom_output_dir(
        self, mock_req_pk, mock_save_csv, mock_save_json, mock_fetch
    ):
        """Test main flow with custom output directory."""
        mock_fetch.return_value = [_event("1", "m1")]

        main()

        paths = [mock_save_json.call_args_list[i][0][1] for i in range(2)]
        for p in paths:
            assert "/tmp/test_output" in p

    @patch("poly_sports.data_fetching.fetch_sports_markets.fetch_sports_markets")
    @patch("poly_sports.data_fetching.fetch_sports_markets.save_json")
    @patch("poly_sports.data_fetching.fetch_sports_markets.save_to_csv")
    @patch("poly_sports.data_fetching.fetch_sports_markets.require_valid_env_private_key")
    @patch.dict(
        os.environ,
        {
            "GAMMA_API_URL": "https://gamma-api.polymarket.com",
            "ENRICH_WITH_CLOB": "false",
            "PK": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        },
        clear=True,
    )
    def test_main_flow_default_env_values(
        self, mock_req_pk, mock_save_csv, mock_save_json, mock_fetch
    ):
        """Test main flow with default environment values."""
        mock_fetch.return_value = [_event("1", "m1")]

        main()

        mock_fetch.assert_called_once()
        assert "gamma-api.polymarket.com" in mock_fetch.call_args[0][0]
