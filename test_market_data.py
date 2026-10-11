import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from market_data import fetch_price_history, normalize_korean_code, yahoo_symbols


def history(*closes: float) -> pd.DataFrame:
    return pd.DataFrame(
        {"Close": list(closes)},
        index=pd.date_range("2026-08-01", periods=len(closes), freq="20D"),
    )


class FakeReader:
    calls = []

    @classmethod
    def DataReader(cls, symbol, start, end):
        cls.calls.append((symbol, start, end))
        return history(100, 110, 120)


class FailingReader:
    calls = 0

    @classmethod
    def DataReader(cls, symbol, start, end):
        cls.calls += 1
        raise RuntimeError("naver unavailable")


class FakeTicker:
    def __init__(self, symbol):
        self.symbol = symbol

    def history(self, **kwargs):
        if self.symbol.endswith(".KS"):
            return pd.DataFrame()
        return history(200, 210, 220)


class FakeYFinance:
    calls = []

    @classmethod
    def Ticker(cls, symbol):
        cls.calls.append(symbol)
        return FakeTicker(symbol)


class MarketDataTest(unittest.TestCase):
    def setUp(self):
        FakeReader.calls = []
        FailingReader.calls = 0
        FakeYFinance.calls = []

    def test_normalizes_domestic_codes(self):
        self.assertEqual(normalize_korean_code("A170920"), "170920")
        self.assertEqual(normalize_korean_code("5930.KS"), "005930")

    def test_domestic_price_uses_naver_first(self):
        result = fetch_price_history(
            "KR",
            "196170",
            "196170.KS",
            reader_module=FakeReader,
            yf_module=FakeYFinance,
            today=date(2026, 10, 11),
        )
        self.assertEqual(result["source"], "NAVER")
        self.assertEqual(result["current"], 120)
        self.assertEqual(FakeReader.calls[0][0], "NAVER:196170")
        self.assertEqual(FakeYFinance.calls, [])

    def test_domestic_fallback_probes_kospi_then_kosdaq(self):
        result = fetch_price_history(
            "KR",
            "170920",
            "170920.KS",
            reader_module=FailingReader,
            yf_module=FakeYFinance,
        )
        self.assertEqual(FailingReader.calls, 2)
        self.assertEqual(FakeYFinance.calls, ["170920.KS", "170920.KQ"])
        self.assertEqual(result["source"], "YAHOO:170920.KQ")
        self.assertEqual(result["current"], 220)

    def test_yahoo_symbol_candidates_do_not_duplicate_mapped_symbol(self):
        self.assertEqual(
            yahoo_symbols("196170", "KR", "196170.KS"),
            ["196170.KS", "196170.KQ"],
        )

    def test_app_reads_password_from_streamlit_secret(self):
        app_source = (Path(__file__).parent / "app.py").read_text(encoding="utf-8")
        self.assertIn('st.secrets["APP_PASSWORD"]', app_source)
        self.assertIn("hmac.compare_digest", app_source)


if __name__ == "__main__":
    unittest.main()

