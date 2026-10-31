"""Read-only crypto market forecasts using the official Kronos model."""
import argparse
import json
import os
from pathlib import Path
import sys

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
UPSTREAM = ROOT / "upstream" / "Kronos"
BINANCE_ENDPOINT = "https://api.binance.com/api/v3/klines"
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
INTERVAL_SECONDS = {"1h": 3600, "4h": 14400}


def get_history(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    if symbol not in SYMBOLS:
        raise ValueError("Unsupported symbol")
    if interval not in INTERVAL_SECONDS:
        raise ValueError("Unsupported interval")
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    response = requests.get(
        BINANCE_ENDPOINT,
        params={"symbol": symbol, "interval": interval, "limit": limit},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list) or not data:
        raise RuntimeError("No Binance candles returned")
    columns = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_base",
        "taker_quote", "ignore",
    ]
    df = pd.DataFrame(data, columns=columns)
    df["timestamps"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    for column in ("open", "high", "low", "close", "volume", "quote_volume"):
        df[column] = pd.to_numeric(df[column], errors="raise")
    df["amount"] = df["quote_volume"]
    close_times = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    df = df.loc[close_times < pd.Timestamp.now(tz="UTC")].copy()
    if len(df) < limit - 1:
        raise RuntimeError("Insufficient completed candles")
    return df.reset_index(drop=True)


def forecast(symbol: str, interval: str, lookback: int, pred_len: int,
             samples: int, device: str) -> dict:
    if not 2 <= lookback <= 512 or not 1 <= pred_len <= 120:
        raise ValueError("lookback must be 2..512; pred_len must be 1..120")
    if not 1 <= samples <= 10:
        raise ValueError("samples must be 1..10")
    if not (UPSTREAM / "model").is_dir():
        raise RuntimeError("Clone official Kronos into upstream/Kronos first")
    sys.path.insert(0, str(UPSTREAM))
    from model import Kronos, KronosTokenizer, KronosPredictor

    history = get_history(symbol, interval, lookback)
    step = pd.Timedelta(seconds=INTERVAL_SECONDS[interval])
    future = pd.Series([
        history["timestamps"].iloc[-1] + step * (index + 1)
        for index in range(pred_len)
    ])
    tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
    model = Kronos.from_pretrained("NeoQuasar/Kronos-small")
    predictor = KronosPredictor(model, tokenizer, device=device, max_context=512)
    predicted = predictor.predict(
        df=history[["open", "high", "low", "close", "volume", "amount"]],
        x_timestamp=history["timestamps"],
        y_timestamp=future,
        pred_len=pred_len,
        T=1.0,
        top_p=0.9,
        sample_count=samples,
    ).reset_index(drop=True)
    predicted["timestamp"] = future.dt.strftime("%Y-%m-%dT%H:%M:%SZ").values
    return {
        "symbol": symbol,
        "interval": interval,
        "historical_last_close": float(history["close"].iloc[-1]),
        "model": "NeoQuasar/Kronos-small",
        "sample_count": samples,
        "forecast": predicted[
            ["timestamp", "open", "high", "low", "close"]
        ].to_dict("records"),
        "disclaimer": "Experimental predictions; not a trading signal",
    }


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="BTCUSDT", choices=SYMBOLS)
    parser.add_argument("--interval", default=os.getenv("INTERVAL", "1h"),
                        choices=tuple(INTERVAL_SECONDS))
    parser.add_argument("--lookback", type=int,
                        default=int(os.getenv("LOOKBACK", "400")))
    parser.add_argument("--pred-len", type=int,
                        default=int(os.getenv("PRED_LEN", "24")))
    parser.add_argument("--samples", type=int,
                        default=int(os.getenv("SAMPLE_COUNT", "1")))
    parser.add_argument("--device", default=os.getenv("DEVICE", "cpu"))
    args = parser.parse_args()
    result = forecast(args.symbol, args.interval, args.lookback,
                      args.pred_len, args.samples, args.device)
    out = ROOT / "outputs"
    out.mkdir(exist_ok=True)
    path = out / f"{args.symbol}_{args.interval}.json"
    path.write_text(json.dumps(result, indent=2, default=str) + "\n")
    print(f"Saved forecast to {path}")


if __name__ == "__main__":
    main()
