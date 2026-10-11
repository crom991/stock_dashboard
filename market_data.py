from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any

import pandas as pd


def normalize_korean_code(ticker: object) -> str:
    """국내 종목코드를 네이버 금융에서 사용하는 6자리 코드로 정규화한다."""
    code = str(ticker).strip().upper()
    if code.endswith((".KS", ".KQ")):
        code = code[:-3]
    if code.startswith("A") and len(code) == 7:
        code = code[1:]
    return code.zfill(6) if code.isdigit() else code


def yahoo_symbols(ticker: object, market: object, mapped_ticker: object) -> list[str]:
    """국내 종목은 KOSPI와 KOSDAQ 심볼을 모두 확인한다."""
    normalized_market = str(market).strip().upper()
    mapped = str(mapped_ticker).strip().upper()
    if normalized_market != "KR":
        return [mapped]

    code = normalize_korean_code(ticker)
    candidates = [mapped, f"{code}.KS", f"{code}.KQ"]
    return list(dict.fromkeys(candidate for candidate in candidates if candidate))


def price_points(history: pd.DataFrame) -> tuple[float, float]:
    """일봉에서 최신 종가와 약 1개월 전 종가를 추출한다."""
    if history is None or history.empty or "Close" not in history.columns:
        raise ValueError("유효한 종가 데이터가 없습니다.")

    closes = pd.to_numeric(history["Close"], errors="coerce").dropna().sort_index()
    closes = closes[closes.map(lambda value: math.isfinite(float(value)) and float(value) > 0)]
    if closes.empty:
        raise ValueError("0보다 큰 유효한 종가가 없습니다.")

    current_price = float(closes.iloc[-1])
    target_date = closes.index[-1] - pd.Timedelta(days=30)
    nearest_index = closes.index.get_indexer([target_date], method="nearest")[0]
    month_ago_price = float(closes.iloc[nearest_index])
    return current_price, month_ago_price


def _fetch_naver_history(
    ticker: object,
    *,
    reader_module: Any | None = None,
    today: date | None = None,
) -> pd.DataFrame:
    if reader_module is None:
        import FinanceDataReader as reader_module

    end = today or date.today()
    start = end - timedelta(days=70)
    code = normalize_korean_code(ticker)
    last_error: Exception | None = None
    for _ in range(2):
        try:
            history = reader_module.DataReader(
                f"NAVER:{code}", start.isoformat(), end.isoformat()
            )
        except Exception as exc:
            last_error = exc
            continue
        if history is not None and not history.empty:
            return history
    raise RuntimeError(f"네이버 금융에서 {code} 일봉을 조회하지 못했습니다.") from last_error


def _fetch_yahoo_history(
    ticker: object,
    market: object,
    mapped_ticker: object,
    *,
    yf_module: Any | None = None,
) -> tuple[pd.DataFrame, str]:
    if yf_module is None:
        import yfinance as yf_module

    last_error: Exception | None = None
    for symbol in yahoo_symbols(ticker, market, mapped_ticker):
        try:
            history = yf_module.Ticker(symbol).history(
                period="2mo", auto_adjust=False, actions=False
            )
        except Exception as exc:
            last_error = exc
            continue
        if history is not None and not history.empty and "Close" in history.columns:
            if pd.to_numeric(history["Close"], errors="coerce").notna().any():
                return history, symbol
    raise RuntimeError("Yahoo Finance에서 유효한 일봉을 조회하지 못했습니다.") from last_error


def fetch_price_history(
    market: object,
    ticker: object,
    mapped_ticker: object,
    *,
    reader_module: Any | None = None,
    yf_module: Any | None = None,
    today: date | None = None,
) -> dict[str, object]:
    """국내는 네이버 우선, 그 외에는 Yahoo로 가격과 1개월 전 가격을 조회한다."""
    normalized_market = str(market).strip().upper()
    errors: list[str] = []

    if normalized_market == "KR":
        try:
            history = _fetch_naver_history(
                ticker, reader_module=reader_module, today=today
            )
            current, month_ago = price_points(history)
            return {
                "current": current,
                "month_ago": month_ago,
                "source": "NAVER",
                "error": None,
            }
        except Exception as exc:
            errors.append(f"NAVER: {exc}")

    try:
        history, symbol = _fetch_yahoo_history(
            ticker, market, mapped_ticker, yf_module=yf_module
        )
        current, month_ago = price_points(history)
        return {
            "current": current,
            "month_ago": month_ago,
            "source": f"YAHOO:{symbol}",
            "error": None,
        }
    except Exception as exc:
        errors.append(f"YAHOO: {exc}")

    return {
        "current": float("nan"),
        "month_ago": float("nan"),
        "source": None,
        "error": "; ".join(errors),
    }

