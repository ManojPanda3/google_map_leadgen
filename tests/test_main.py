"""Tests for main module (CLI)."""

import os
import tempfile
from unittest.mock import AsyncMock, patch

import pytest

from google_map_leadgen.main import main, save_to_csv


class TestSaveToCSV:
    def test_save_empty_results(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            filename = f.name

        try:
            save_to_csv([], filename)
            assert not os.path.exists(filename) or os.path.getsize(filename) == 0
        finally:
            if os.path.exists(filename):
                os.unlink(filename)

    def test_save_results_creates_file(self):
        results = [
            {
                "name": "Business 1",
                "address": "123 Main St",
                "phone": "555-1234",
                "website": "https://example.com",
            }
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            filename = f.name

        try:
            save_to_csv(results, filename)
            assert os.path.exists(filename)

            with open(filename) as f:
                content = f.read()
                assert "Business 1" in content
                assert "123 Main St" in content
        finally:
            if os.path.exists(filename):
                os.unlink(filename)

    def test_save_multiple_results(self):
        results = [
            {
                "name": "Business 1",
                "address": "Address 1",
                "phone": "Phone 1",
                "website": "Website 1",
            },
            {
                "name": "Business 2",
                "address": "Address 2",
                "phone": "Phone 2",
                "website": "Website 2",
            },
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            filename = f.name

        try:
            save_to_csv(results, filename)

            with open(filename) as f:
                content = f.read()
                assert "Business 1" in content
                assert "Business 2" in content
        finally:
            if os.path.exists(filename):
                os.unlink(filename)


class TestMainCLI:
    @pytest.mark.asyncio
    async def test_main_exits_without_query(self):
        with pytest.raises(SystemExit):
            await main()

    @pytest.mark.asyncio
    async def test_main_calls_scrape_with_query(self):
        with patch(
            "google_map_leadgen.main.scrape", new_callable=AsyncMock
        ) as mock_scrape:
            mock_scrape.return_value = [{"name": "Test Business"}]

            with patch("sys.argv", ["google_map_leadgen.main", "test query"]):
                with patch("google_map_leadgen.main.save_to_csv"):
                    await main()
                    # It should call with default target and max_tabs from config
                    mock_scrape.assert_called_once()
                    args, kwargs = mock_scrape.call_args
                    assert args[0] == "test query"

    @pytest.mark.asyncio
    async def test_main_calls_scrape_with_custom_params(self):
        with patch(
            "google_map_leadgen.main.scrape", new_callable=AsyncMock
        ) as mock_scrape:
            mock_scrape.return_value = [{"name": "Test Business"}]

            with patch(
                "sys.argv",
                [
                    "google_map_leadgen.main",
                    "test query",
                    "--leads",
                    "10",
                    "--tabs",
                    "5",
                ],
            ):
                with patch("google_map_leadgen.main.save_to_csv"):
                    await main()
                    mock_scrape.assert_called_once_with(
                        "test query", target=10, max_tabs=5
                    )

    @pytest.mark.asyncio
    async def test_main_outputs_json(self):
        results = [{"name": "Test Business", "address": "Test Address"}]

        with patch(
            "google_map_leadgen.main.scrape", new_callable=AsyncMock
        ) as mock_scrape:
            mock_scrape.return_value = results

            with patch("sys.argv", ["google_map_leadgen.main", "test query", "--json"]):
                with patch("builtins.print") as mock_print:
                    await main()
                    printed_output = "".join(
                        str(call.args[0]) for call in mock_print.call_args_list
                    )
                    assert "Test Business" in printed_output
