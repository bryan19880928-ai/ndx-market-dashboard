from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SYMBOLS_PATH = ROOT / "data" / "symbols.json"
OUTPUT_PATH = ROOT / "data" / "market.json"
RISK_SYMBOLS = [
    {"id": "VIX", "symbol": "^VIX", "name": "CBOE Volatility Index", "type": "risk"},
    {"id": "TNX", "symbol": "^TNX", "name": "US 10Y Treasury Yield", "type": "risk"},
]


def fetch_chart(symbol: str, range_: str = "1y") -> dict:
    encoded = quote(symbol, safe="")
    hosts = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]
    last_error: Exception | None = None
    for attempt in range(5):
        host = hosts[attempt % len(hosts)]
        url = (
            f"https://{host}/v8/finance/chart/{encoded}"
            f"?range={range_}&interval=1d&events=history&includeAdjustedClose=true"
        )
        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json,text/plain,*/*",
            },
        )
        try:
            with urlopen(req, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            error = payload.get("chart", {}).get("error")
            if error:
                raise RuntimeError(error)
            result = payload["chart"]["result"][0]
            bars = parse_bars(result)
            if len(bars) < 20:
                raise RuntimeError(f"Not enough data for {symbol}")
            return {
                "meta": {
                    "currency": result.get("meta", {}).get("currency"),
                    "exchange": result.get("meta", {}).get("fullExchangeName"),
                    "timezone": result.get("meta", {}).get("exchangeTimezoneName"),
                    "regularMarketTime": result.get("meta", {}).get("regularMarketTime"),
                },
                "bars": bars,
            }
        except (HTTPError, URLError, TimeoutError, RuntimeError, KeyError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(2 + attempt * 2)
    raise RuntimeError(f"Unable to fetch {symbol}: {last_error}")


def parse_bars(result: dict) -> list[dict]:
    timestamps = result.get("timestamp") or []
    quote_data = result["indicators"]["quote"][0]
    adjclose = result["indicators"].get("adjclose", [{}])[0].get("adjclose", [])
    bars: list[dict] = []
    for index, ts in enumerate(timestamps):
        close = adjclose[index] if index < len(adjclose) and adjclose[index] is not None else quote_data["close"][index]
        if close is None:
            continue
        bars.append(
            {
                "date": datetime.fromtimestamp(ts, timezone.utc).date().isoformat(),
                "close": round(float(close), 6),
                "open": round(float(quote_data["open"][index]), 6) if quote_data["open"][index] is not None else None,
                "high": round(float(quote_data["high"][index]), 6) if quote_data["high"][index] is not None else None,
                "low": round(float(quote_data["low"][index]), 6) if quote_data["low"][index] is not None else None,
                "volume": quote_data.get("volume", [None] * len(timestamps))[index],
            }
        )
    return bars


def load_symbols() -> list[dict]:
    configured = json.loads(SYMBOLS_PATH.read_text(encoding="utf-8"))
    return configured + RISK_SYMBOLS


def main() -> None:
    symbols = load_symbols()
    output = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Yahoo Finance chart API",
        "symbols": {},
        "errors": {},
    }
    for item in symbols:
        try:
            chart = fetch_chart(item["symbol"])
            output["symbols"][item["id"]] = {**item, **chart}
            print(f"ok {item['id']} {chart['bars'][-1]['date']}")
        except Exception as exc:
            output["errors"][item["id"]] = str(exc)
            print(f"error {item['id']}: {exc}")
    if "NDX" not in output["symbols"]:
        raise SystemExit("NDX is required but was not fetched.")
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
